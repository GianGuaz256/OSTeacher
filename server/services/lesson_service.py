from typing import Optional, Dict, Any
from supabase import Client
import json
from agno.run.response import RunResponse
import logging

from ..repositories.course_repository import CourseRepository
from ..repositories.lesson_repository import LessonRepository
from ..agents.lesson_content_agent import LessonContentAgent
from ..utils.helpers import extract_external_links
from ..utils.retry_utils import is_retryable_error
from ..models import CourseDifficulty, LessonStatus, UserLessonStatus, UserCourseStatus

logger = logging.getLogger(__name__)

class LessonService:
    """Service for lesson business logic."""
    
    def __init__(self, db: Client):
        self.course_repo = CourseRepository(db)
        self.lesson_repo = LessonRepository(db)
        self.db = db
    
    def regenerate_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Regenerates the content for a specific lesson using the LessonContentAgent."""
        try:
            # 1. Fetch the lesson to regenerate
            lesson_data = self.lesson_repo.get_with_course_info(lesson_id)
            
            if not lesson_data:
                logger.error(f"Lesson with ID {lesson_id} not found for regeneration.")
                return None
        
            current_lesson_title = lesson_data.get('title')
            planned_description = lesson_data.get('planned_description')
            
            course_info = lesson_data.get('courses')

            if not isinstance(course_info, dict):
                course_id_from_lesson = lesson_data.get('course_id')
                if not course_id_from_lesson:
                    error_msg = "Regeneration failed: Missing course association."
                    logger.error(f"Error: Lesson {lesson_id} has no course_id and course data was not joined correctly.")
                    self.lesson_repo.update(lesson_id, {
                        "generation_status": LessonStatus.GENERATION_FAILED.value,
                        "content_md": error_msg
                    })
                    return None

                logger.info(f"Course data not fully joined for lesson {lesson_id}. Fetching course {course_id_from_lesson} separately.")
                parent_course_data = self.course_repo.get_by_id(course_id_from_lesson)
                if not parent_course_data:
                    error_msg = "Regeneration failed: Parent course not found."
                    logger.error(f"Error: Parent course {course_id_from_lesson} not found for lesson {lesson_id}.")
                    self.lesson_repo.update(lesson_id, {
                        "generation_status": LessonStatus.GENERATION_FAILED.value,
                        "content_md": error_msg
                    })
                    return None
                course_info = parent_course_data

            if not course_info or not course_info.get('subject') or not course_info.get('difficulty'):
                error_msg = "Regeneration failed: Course subject/difficulty missing."
                logger.error(f"Error: Critical course information (subject or difficulty) is missing for lesson {lesson_id}. Course info: {course_info}")
                self.lesson_repo.update(lesson_id, {
                    "generation_status": LessonStatus.GENERATION_FAILED.value,
                    "content_md": error_msg
                })
                return None

            course_subject = course_info.get('subject')
            course_difficulty_str = course_info.get('difficulty')
            
            try:
                course_difficulty_enum_val = CourseDifficulty(course_difficulty_str).value if course_difficulty_str else CourseDifficulty.MEDIUM.value
            except ValueError:
                logger.warning(f"Invalid course difficulty '{course_difficulty_str}' for lesson {lesson_id}. Defaulting to MEDIUM.")
                course_difficulty_enum_val = CourseDifficulty.MEDIUM.value

            # 2. Update lesson status to 'generating' and clear old content/links
            self.lesson_repo.update(lesson_id, {
                "generation_status": LessonStatus.GENERATING.value, 
                "content_md": "Generating new content...",
                "external_links": json.dumps([])
            })
            logger.info(f"Set status to 'generating' for lesson ID: {lesson_id}")

            # 3. Configure LessonContentAgent and generate content
            lesson_agent = LessonContentAgent()

            # 4. Construct query and run agent
            lesson_content_query = (
                f"Lesson Title: {current_lesson_title}\\n"
                f"Lesson Description: {planned_description or 'No specific planned description available.'}\\n"
                f"Overall Course Subject: {course_subject}\\n"
                f"Overall Course Difficulty: {course_difficulty_enum_val}"
            )
            
            logger.info(f"Generating content for lesson: '{current_lesson_title}' (ID: {lesson_id})")
            lesson_content_response = lesson_agent.run(lesson_content_query)
            
            # 5. Process response and update lesson
            if lesson_content_response and hasattr(lesson_content_response, 'content') and \
               lesson_content_response.content and isinstance(lesson_content_response.content, str):
                
                extracted_links = extract_external_links(lesson_content_response.content)
                
                lesson_update_data = {
                    "content_md": lesson_content_response.content,
                    "external_links": json.dumps(extracted_links), 
                    "generation_status": LessonStatus.COMPLETED.value
                }
                updated_lesson = self.lesson_repo.update(lesson_id, lesson_update_data)

                if updated_lesson:
                    logger.info(f"Content successfully regenerated and saved for lesson ID: {lesson_id}")
                    return updated_lesson
                else:
                    error_msg = f"Failed to save after regeneration. Original generated content (first 200 chars): {lesson_content_response.content[:200]}..."
                    logger.error(f"Failed to save regenerated content for lesson ID: {lesson_id}")
                    self.lesson_repo.update(lesson_id, {
                        "generation_status": LessonStatus.GENERATION_FAILED.value, 
                        "content_md": error_msg
                    })
                    return self.lesson_repo.get_by_id(lesson_id)
            else:
                # Handle error response from agent
                agent_error_msg = "Agent returned no content or an invalid response."
                if lesson_content_response and hasattr(lesson_content_response, 'error') and lesson_content_response.error:
                    agent_error_msg = str(lesson_content_response.error)
                    
                    # Check if this was a retryable error that exhausted retries
                    if is_retryable_error(Exception(lesson_content_response.error)):
                        agent_error_msg = f"Connection issues prevented content generation after multiple retries: {lesson_content_response.error}"
                elif not lesson_content_response:
                    agent_error_msg = "Agent did not return a response object."
                
                logger.error(f"Failed to generate content for lesson ID: {lesson_id}. Agent Error: {agent_error_msg}")
                self.lesson_repo.update(lesson_id, {
                    "generation_status": LessonStatus.GENERATION_FAILED.value,
                    "content_md": f"Content generation failed. {agent_error_msg}"
                })
                return self.lesson_repo.get_by_id(lesson_id)

        except Exception as e:
            error_msg = f"Critical exception during regeneration: {str(e)[:500]}"
            logger.error(f"An unexpected exception occurred during lesson regeneration for ID {lesson_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Attempt to update lesson status to reflect failure due to exception
            if lesson_id:
                try:
                    # Check if this was a connection error
                    if is_retryable_error(e):
                        error_msg = f"Connection issues prevented regeneration: {str(e)[:500]}"
                    
                    self.lesson_repo.update(lesson_id, {
                        "generation_status": LessonStatus.GENERATION_FAILED.value,
                        "content_md": error_msg
                    })
                except Exception as db_update_err:
                    logger.error(f"Additionally, failed to update lesson status to FAILED after critical exception: {db_update_err}")
            
            return None

    def update_lesson_user_status(self, lesson_id: str, new_user_status: UserLessonStatus) -> Optional[Dict[str, Any]]:
        """Updates the user-facing status of a lesson and then checks course completion."""
        try:
            # Validate if new_user_status is a valid UserLessonStatus enum member
            if not isinstance(new_user_status, UserLessonStatus):
                try:
                    new_user_status_enum = UserLessonStatus(new_user_status)
                except ValueError:
                    print(f"Invalid UserLessonStatus provided: {new_user_status}")
                    return None
            else:
                new_user_status_enum = new_user_status

            updated_lesson = self.lesson_repo.update(lesson_id, {"user_facing_status": new_user_status_enum.value})
            
            if updated_lesson:
                course_id = updated_lesson.get("course_id")
                if course_id:
                    self._check_and_update_course_completion_status(course_id)
                
                return updated_lesson
            else:
                print(f"Failed to update user-facing status for lesson {lesson_id}")
                return None
                
        except Exception as e:
            print(f"Error updating lesson user-facing status for {lesson_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _check_and_update_course_completion_status(self, course_id: str) -> None:
        """Checks if all lessons in a course are completed and updates the course status accordingly."""
        try:
            # Fetch the course to ensure it exists and to get its current user-facing status
            course_data = self.course_repo.get_by_id(course_id)
            if not course_data:
                print(f"_check_and_update_course_completion_status: Course {course_id} not found.")
                return
            
            current_course_user_status = course_data.get('status')  # This should already be mapped from 'user_facing_status'

            # Fetch all lessons for the course, specifically their user-facing status
            lessons = self.lesson_repo.get_by_course_id(course_id)
            
            new_course_user_status_value = None

            if not lessons:
                # No lessons in the course.
                if current_course_user_status in [UserCourseStatus.COMPLETED.value, UserCourseStatus.IN_PROGRESS.value]:
                    new_course_user_status_value = UserCourseStatus.NOT_STARTED.value
                elif not current_course_user_status:
                    new_course_user_status_value = UserCourseStatus.NOT_STARTED.value
            else:
                lessons_statuses = [lesson.get('status') for lesson in lessons]  # This should already be mapped from 'user_facing_status'
                
                all_lessons_completed = all(status == UserLessonStatus.COMPLETED.value for status in lessons_statuses)
                any_lesson_in_progress = any(status == UserLessonStatus.IN_PROGRESS.value for status in lessons_statuses)
                any_lesson_completed = any(status == UserLessonStatus.COMPLETED.value for status in lessons_statuses)

                if all_lessons_completed:
                    new_course_user_status_value = UserCourseStatus.COMPLETED.value
                elif any_lesson_in_progress or any_lesson_completed:
                    new_course_user_status_value = UserCourseStatus.IN_PROGRESS.value
                else:
                    new_course_user_status_value = UserCourseStatus.NOT_STARTED.value

            if new_course_user_status_value and new_course_user_status_value != current_course_user_status:
                self.course_repo.update(course_id, {"user_facing_status": new_course_user_status_value})
                print(f"Course {course_id} user-facing status updated from '{current_course_user_status}' to: '{new_course_user_status_value}'")
            elif new_course_user_status_value == current_course_user_status:
                print(f"Course {course_id} user-facing status '{current_course_user_status}' is already correct. No update needed.")
            else:
                print(f"Course {course_id} user-facing status '{current_course_user_status}' requires no change based on current logic path.")

        except Exception as e:
            print(f"Error in _check_and_update_course_completion_status for course {course_id}: {e}") 