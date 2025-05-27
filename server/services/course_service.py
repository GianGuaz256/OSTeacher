from typing import Optional, Dict, Any, List
from supabase import Client
import uuid
import json
import re
import threading
from agno.run.response import RunResponse
from pydantic import ValidationError
import logging

from ..repositories.course_repository import CourseRepository
from ..repositories.lesson_repository import LessonRepository
from ..agents.course_planner_agent import CoursePlannerAgent
from ..agents.lesson_content_agent import LessonContentAgent
from ..services.quiz_service import QuizService
from ..utils.parsers import CourseParser
from ..utils.helpers import extract_external_links
from ..utils.retry_utils import is_retryable_error
from ..models import (
    CourseDifficulty, CourseStatus, UserCourseStatus, 
    LessonStatus, UserLessonStatus, LessonOutlineItem,
    CourseUpdateRequest, CourseField
)

logger = logging.getLogger(__name__)

class CourseService:
    """Service for course business logic."""
    
    def __init__(self, db: Client):
        self.course_repo = CourseRepository(db)
        self.lesson_repo = LessonRepository(db)
        self.quiz_service = QuizService(db)
        self.course_parser = CourseParser()
        self.db = db
    
    def get_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single course by its ID, including its lessons."""
        course_data = self.course_repo.get_by_id(course_id)
        if not course_data:
            return None
        
        # Get lessons for this course
        lessons = self.lesson_repo.get_by_course_id(course_id)
        course_data['lessons'] = lessons
        
        return course_data
    
    def get_all_courses(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves all courses with pagination, including their lessons."""
        courses_data = self.course_repo.get_all(skip, limit)
        if not courses_data:
            return []
        
        course_ids = [course['id'] for course in courses_data]
        lessons_by_course_id = self.lesson_repo.get_by_course_ids(course_ids)
        
        for course in courses_data:
            course['lessons'] = lessons_by_course_id.get(course['id'], [])
        
        return courses_data
    
    def update_course(self, course_id: str, course_update_request: CourseUpdateRequest) -> Optional[Dict[str, Any]]:
        """Updates an existing course by its ID."""
        try:
            # Fetch the existing course
            existing_course = self.course_repo.get_by_id(course_id)
            if not existing_course:
                logger.error(f"Course with ID {course_id} not found for update.")
                return None

            # Prepare update data
            update_data = {}
            if course_update_request.title is not None:
                update_data["title"] = course_update_request.title
            if course_update_request.description is not None:
                update_data["description"] = course_update_request.description
            if course_update_request.icon is not None:
                update_data["icon"] = course_update_request.icon

            # Handle lesson outline plan update
            if course_update_request.lesson_outline_plan is not None:
                new_lesson_outline_plan = [item.dict() for item in course_update_request.lesson_outline_plan]
                update_data["lesson_outline_plan"] = new_lesson_outline_plan
                
                # Delete existing lessons and recreate them
                logger.info(f"Updating lesson outline for course {course_id}. Deleting existing lessons.")
                self.lesson_repo.delete_by_course_id(course_id)
                
                # Recreate lessons based on the new_lesson_outline_plan
                for item_dict in new_lesson_outline_plan:
                    lesson_outline = LessonOutlineItem(**item_dict)
                    lesson_placeholder_data = {
                        "course_id": course_id,
                        "title": lesson_outline.planned_title,
                        "planned_description": lesson_outline.planned_description,
                        "order_in_course": lesson_outline.order,
                        "generation_status": LessonStatus.PLANNED.value,
                        "user_facing_status": UserLessonStatus.NOT_STARTED.value
                    }
                    insert_lesson_resp = self.lesson_repo.create(lesson_placeholder_data)
                    if not insert_lesson_resp:
                        logger.error(f"Error inserting new lesson placeholder for '{lesson_outline.planned_title}' during course update")

                logger.info(f"Lessons repopulated based on new plan for course {course_id}. Content regeneration may be needed separately.")

            # Fetch and return the updated course with its (potentially new) lessons
            return self.get_course(course_id)
                
        except Exception as e:
            logger.error(f"An exception occurred during course update for {course_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_course_with_team(self, initial_title: str, subject: str, difficulty: CourseDifficulty, has_quizzes: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generates a course using an Agent Team (Planner and Lesson Content agents),
        saves the course outline, then incrementally creates and generates content for each lesson.
        """
        try:
            # Validate has_quizzes requirement
            if not has_quizzes:
                logger.error("Course creation rejected: has_quizzes must be True. All courses must have quizzes enabled.")
                raise ValueError("Course creation requires has_quizzes to be True. All courses must have quizzes enabled for educational quality.")

            # Generate course plan using AI
            plan_data = self._generate_course_plan(initial_title, subject, difficulty, has_quizzes)
            if not plan_data:
                logger.error("Failed to generate course plan")
                return None

            # Generate unique course ID
            course_id = str(uuid.uuid4())
            
            # Prepare course data for database
            course_data = self._prepare_course_data(course_id, plan_data, subject, difficulty, has_quizzes)
            
            # Save initial course to database
            saved_course = self.course_repo.create(course_data)
            if not saved_course:
                logger.error("Failed to save initial course to database")
                return None
            
            logger.info(f"Successfully saved initial course with ID: {course_id}")
            
            # Start background lesson generation
            self._generate_lessons_async(course_id, plan_data, subject, difficulty, has_quizzes)
            
            # Return the course immediately (lessons will be generated in background)
            return self.get_course(course_id)
            
        except Exception as e:
            logger.error(f"An exception occurred during course creation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_course_plan(self, title: str, subject: str, difficulty: CourseDifficulty, has_quizzes: bool) -> Optional[Dict]:
        """Generate course plan using AI agent."""
        try:
            planner_agent = CoursePlannerAgent()
            
            planner_query = (
                f"Subject: {subject}\\n"
                f"Initial Title: {title}\\n"
                f"Difficulty Level: {difficulty.value}\\n"
                f"Has Quizzes: {has_quizzes}"
            )
            
            logger.info(f"Running CoursePlannerAgent for: '{title}' on '{subject}'...")
            planner_response = planner_agent.run(planner_query)
            
            # Handle error response from agent
            if hasattr(planner_response, 'error') and planner_response.error:
                error_msg = str(planner_response.error)
                if is_retryable_error(Exception(planner_response.error)):
                    logger.error(f"Course planning failed due to connection issues: {error_msg}")
                else:
                    logger.error(f"Course planning failed: {error_msg}")
                return None
            
            if not planner_response or not hasattr(planner_response, 'content') or not planner_response.content:
                logger.error("CoursePlannerAgent returned no content")
                return None
            
            logger.info(f"Planner agent returned {len(planner_response.content)} characters of content")
            
            # Parse JSON response
            try:
                plan_data = json.loads(planner_response.content)
                
                # Validate required fields
                required_fields = ["courseTitle", "courseDescription", "lesson_outline_plan"]
                for field in required_fields:
                    if field not in plan_data:
                        logger.error(f"Missing required field '{field}' in course plan")
                        return None
                
                # Validate lesson outline
                if not isinstance(plan_data["lesson_outline_plan"], list) or len(plan_data["lesson_outline_plan"]) == 0:
                    logger.error("Invalid or empty lesson_outline_plan")
                    return None
                
                logger.info(f"CoursePlannerAgent successfully generated a plan for {len(plan_data['lesson_outline_plan'])} lessons.")
                return plan_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from CoursePlannerAgent: {e}")
                logger.error(f"Raw content: {planner_response.content[:500]}...")
                return None
                
        except Exception as e:
            logger.error(f"An exception occurred during CoursePlannerAgent execution: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _prepare_course_data(self, course_id: str, plan_data: Dict, subject: str, difficulty: CourseDifficulty, has_quizzes: bool) -> Dict[str, Any]:
        """Prepare course data for database insertion."""
        # Parse the field from the AI response
        course_field = None
        if "courseField" in plan_data:
            try:
                course_field = CourseField(plan_data["courseField"].lower())
            except ValueError:
                logger.warning(f"Invalid field '{plan_data['courseField']}' from AI. Using None.")
                course_field = None
        
        return {
            "id": course_id,
            "title": plan_data.get("courseTitle", "Untitled Course"),
            "subject": subject,
            "description": plan_data.get("courseDescription", f"A course on {subject}."),
            "difficulty": difficulty.value,
            "field": course_field.value if course_field else None,
            "icon": plan_data.get("courseIcon"),
            "lesson_outline_plan": plan_data["lesson_outline_plan"],
            "generation_status": CourseStatus.DRAFT.value,
            "user_facing_status": UserCourseStatus.NOT_STARTED.value,
            "has_quizzes": has_quizzes
        }

    def _generate_lessons_async(self, course_id: str, plan_data: Dict, subject: str, difficulty: CourseDifficulty, has_quizzes: bool):
        """Generate lessons in background thread."""
        def generate_lessons():
            try:
                lesson_agent = LessonContentAgent()
                
                # Update course status to generating
                self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATING.value})
                
                for lesson_outline_item_dict in plan_data["lesson_outline_plan"]:
                    lesson_outline = LessonOutlineItem(**lesson_outline_item_dict)

                    lesson_placeholder_data = {
                        "course_id": course_id,
                        "title": lesson_outline.planned_title,
                        "planned_description": lesson_outline.planned_description,
                        "order_in_course": lesson_outline.order,
                        "generation_status": LessonStatus.PLANNED.value,
                        "user_facing_status": UserLessonStatus.NOT_STARTED.value,
                        "has_quiz": lesson_outline.has_quiz  # Include quiz flag from planner
                    }
                    
                    try:
                        logger.info(f"Creating placeholder for lesson: '{lesson_outline.planned_title}'")
                        placeholder_response = self.lesson_repo.create(lesson_placeholder_data)
                        if not placeholder_response or not placeholder_response.get('id'):
                            logger.error(f"Error creating placeholder for lesson '{lesson_outline.planned_title}'.")
                            continue

                        lesson_id = placeholder_response['id']
                        logger.info(f"Placeholder lesson created with ID: {lesson_id}")

                        # Update status to 'generating' before calling agent
                        self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATING.value})

                        logger.info(f"Generating content for lesson: '{lesson_outline.planned_title}' (ID: {lesson_id})")
                        lesson_content_query = (
                            f"Lesson Title: {lesson_outline.planned_title}\\n"
                            f"Lesson Description: {lesson_outline.planned_description}\\n"
                            f"Overall Course Subject: {subject}\\n"
                            f"Overall Course Difficulty: {difficulty.value}"
                        )
                        
                        lesson_content_response = lesson_agent.run(lesson_content_query)
                        
                        # Handle successful response
                        if lesson_content_response and hasattr(lesson_content_response, 'content') and lesson_content_response.content:
                            # Extract links
                            extracted_links = extract_external_links(lesson_content_response.content)
                            
                            lesson_update_data = {
                                "content_md": lesson_content_response.content,
                                "external_links": json.dumps(extracted_links),
                                "generation_status": LessonStatus.COMPLETED.value
                            }
                            self.lesson_repo.update(lesson_id, lesson_update_data)
                            logger.info(f"Content generated and saved for lesson ID: {lesson_id}")
                            
                            # Generate quiz if lesson should have one
                            if lesson_outline.has_quiz:
                                logger.info(f"Generating quiz for lesson: '{lesson_outline.planned_title}' (ID: {lesson_id})")
                                try:
                                    quiz_result = self.quiz_service.create_quiz_for_lesson(course_id, lesson_id)
                                    if quiz_result:
                                        logger.info(f"Quiz successfully generated for lesson ID: {lesson_id}")
                                    else:
                                        logger.error(f"Failed to generate quiz for lesson ID: {lesson_id}")
                                except Exception as quiz_error:
                                    logger.error(f"Error generating quiz for lesson ID {lesson_id}: {quiz_error}")
                        else:
                            # Handle error response from agent
                            error_msg = "No content generated"
                            if hasattr(lesson_content_response, 'error') and lesson_content_response.error:
                                error_msg = str(lesson_content_response.error)
                                if is_retryable_error(Exception(lesson_content_response.error)):
                                    error_msg = f"Connection issues prevented content generation: {lesson_content_response.error}"
                            
                            logger.error(f"Failed to generate content for lesson ID: {lesson_id}. Error: {error_msg}")
                            self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATION_FAILED.value})
                    
                    except Exception as e_lesson:
                        error_msg = f"Exception during lesson processing for '{lesson_outline.planned_title}': {e_lesson}"
                        if is_retryable_error(e_lesson):
                            error_msg = f"Connection issues during lesson processing for '{lesson_outline.planned_title}': {e_lesson}"
                        
                        logger.error(error_msg)
                        import traceback
                        traceback.print_exc()
                        if 'lesson_id' in locals():
                            self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATION_FAILED.value})
                        continue

                # Create final quiz if quizzes are enabled
                if has_quizzes:
                    logger.info(f"Creating final quiz for course ID: {course_id}")
                    try:
                        final_quiz_result = self.quiz_service.create_final_quiz_for_course(course_id)
                        if final_quiz_result:
                            logger.info(f"Final quiz successfully generated for course ID: {course_id}")
                        else:
                            logger.error(f"Failed to generate final quiz for course ID: {course_id}")
                    except Exception as final_quiz_error:
                        logger.error(f"Error generating final quiz for course ID {course_id}: {final_quiz_error}")

                # Update course generation status to COMPLETED
                logger.info(f"Lesson generation loop finished for course ID: {course_id}. Setting course generation_status to COMPLETED.")
                self.course_repo.update(course_id, {"generation_status": CourseStatus.COMPLETED.value})
                
            except Exception as e:
                error_msg = f"Exception in background lesson generation for course ID {course_id}: {e}"
                if is_retryable_error(e):
                    error_msg = f"Connection issues in background lesson generation for course ID {course_id}: {e}"
                
                logger.error(error_msg)
                import traceback
                traceback.print_exc()
                
                # Update course status to failed
                try:
                    self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATION_FAILED.value})
                except Exception as db_update_err:
                    logger.error(f"Failed to update course status to GENERATION_FAILED after background exception: {db_update_err}")
        
        # Start the background thread
        background_thread = threading.Thread(target=generate_lessons)
        background_thread.daemon = True
        background_thread.start()

    def retry_course_generation(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Retries course generation by deleting all existing lessons and recreating them from scratch.
        Uses the course's lesson_outline_plan JSON to recreate all lessons.
        """
        try:
            # Fetch the course to ensure it exists and get the lesson plan
            course_data = self.course_repo.get_by_id(course_id)
            if not course_data:
                logger.error(f"Course with ID {course_id} not found for retry.")
                return None
            
            course_subject = course_data.get('subject', 'General')
            lesson_outline_plan = course_data.get('lesson_outline_plan', [])
            
            if not lesson_outline_plan or not isinstance(lesson_outline_plan, list):
                logger.error(f"Course {course_id} has no valid lesson_outline_plan. Cannot retry generation.")
                return None
            
            # Parse difficulty
            course_difficulty_str = course_data.get('difficulty', 'medium')
            try:
                course_difficulty_enum = CourseDifficulty(course_difficulty_str.lower())
            except ValueError:
                course_difficulty_enum = CourseDifficulty.MEDIUM
            
            logger.info(f"Starting complete retry generation for course: {course_data.get('title')} (ID: {course_id})")
            logger.info(f"Will recreate {len(lesson_outline_plan)} lessons from the course plan")
            
            # Delete all existing lessons for this course
            logger.info(f"Deleting all existing lessons for course {course_id}")
            self.lesson_repo.delete_by_course_id(course_id)
            
            # Update course status to 'generating'
            self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATING.value})
            
            # Start background generation process
            self._generate_lessons_async(course_id, {"lesson_outline_plan": lesson_outline_plan}, course_subject, course_difficulty_enum, course_data.get('has_quizzes', False))
            
            logger.info(f"Background lesson generation started for course ID: {course_id}")
            
            # Return the current course state immediately (with no lessons since we deleted them)
            return self.get_course(course_id)
            
        except Exception as e:
            logger.error(f"An unexpected exception occurred during course retry generation setup for ID {course_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update course status to failed if possible
            try:
                self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATION_FAILED.value})
            except Exception as db_update_err:
                logger.error(f"Additionally, failed to update course status to GENERATION_FAILED after exception: {db_update_err}")
            
            return None