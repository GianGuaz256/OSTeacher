from typing import Optional, Dict, Any, List
from supabase import Client
import uuid
import json
import re
import threading
from agno.run.response import RunResponse
from pydantic import ValidationError

from ..repositories.course_repository import CourseRepository
from ..repositories.lesson_repository import LessonRepository
from ..agents.course_planner_agent import CoursePlannerAgent
from ..agents.lesson_content_agent import LessonContentAgent
from ..utils.parsers import CourseParser
from ..utils.helpers import extract_external_links
from ..models import (
    CourseDifficulty, CourseStatus, UserCourseStatus, 
    LessonStatus, UserLessonStatus, LessonOutlineItem,
    CourseUpdateRequest
)

class CourseService:
    """Service for course business logic."""
    
    def __init__(self, db: Client):
        self.course_repo = CourseRepository(db)
        self.lesson_repo = LessonRepository(db)
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
        update_data_dict = course_update_request.model_dump(exclude_unset=True)
        
        # Handle status mapping for user-facing status
        if 'status' in update_data_dict and hasattr(update_data_dict['status'], 'value'):
            update_data_dict['user_facing_status'] = update_data_dict.pop('status').value
        elif 'status' in update_data_dict:
            # If status is present but not an enum, remove it to avoid confusion
            update_data_dict.pop('status')

        # Separate lesson_outline_plan for special handling if it exists
        new_lesson_outline_plan = update_data_dict.pop('lesson_outline_plan', None)

        if not update_data_dict and new_lesson_outline_plan is None:
            return self.get_course(course_id)

        try:
            # Update scalar fields of the course
            if update_data_dict:
                updated_course = self.course_repo.update(course_id, update_data_dict)
                if not updated_course:
                    if not self.course_repo.exists(course_id):
                        return None
                    print(f"Course {course_id} exists, but update failed.")

            # Handle lesson_outline_plan update
            if new_lesson_outline_plan is not None:
                print(f"Updating lesson_outline_plan for course {course_id}.")
                # Save the new plan to the course itself
                plan_update_response = self.course_repo.update(course_id, {"lesson_outline_plan": new_lesson_outline_plan})
                if not plan_update_response:
                    print(f"Error updating lesson_outline_plan for course {course_id}")

                # Delete all existing lessons and recreate them based on the new plan
                print(f"Deleting existing lessons for course {course_id} before repopulating based on new plan.")
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
                        print(f"Error inserting new lesson placeholder for '{lesson_outline.planned_title}' during course update")

                print(f"Lessons repopulated based on new plan for course {course_id}. Content regeneration may be needed separately.")

            # Fetch and return the updated course with its (potentially new) lessons
            return self.get_course(course_id)
                
        except Exception as e:
            print(f"An exception occurred during course update for {course_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_course_with_team(self, initial_title: str, subject: str, difficulty: CourseDifficulty) -> Optional[Dict[str, Any]]:
        """
        Generates a course using an Agent Team (Planner and Lesson Content agents),
        saves the course outline, then incrementally creates and generates content for each lesson.
        """
        course_id = str(uuid.uuid4())

        try:
            # Step 1: Generate course plan
            plan_data = self._generate_course_plan(initial_title, subject, difficulty)
            if not plan_data:
                return None

            # Step 2: Save initial course
            course_data = self._prepare_course_data(course_id, plan_data, subject, difficulty)
            created_course = self.course_repo.create(course_data)
            if not created_course:
                return None

            print(f"Successfully saved initial course with ID: {course_id}")

            # Step 3: Generate lessons (background task)
            self._generate_lessons_async(course_id, plan_data, subject, difficulty)

            return self.get_course(course_id)

        except Exception as e:
            print(f"Exception creating course: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_course_plan(self, title: str, subject: str, difficulty: CourseDifficulty) -> Optional[Dict]:
        """Generate course plan using AI agent."""
        planner = CoursePlannerAgent()
        query = f"Plan a course on '{subject}' titled '{title}' for difficulty '{difficulty.value}'. Generate 5-10 lessons."
        
        try:
            print(f"Running CoursePlannerAgent for: '{title}' on '{subject}'...")
            planner_response_obj = planner.run(query)

            if not isinstance(planner_response_obj, RunResponse) or not planner_response_obj.content:
                error_msg = getattr(planner_response_obj, 'error', "Planner agent did not return a valid RunResponse object or content.")
                print(f"Error: {error_msg}")
                return None

            planner_content_str = planner_response_obj.content
            print(f"Planner agent returned {len(planner_content_str)} characters of content")

            # Parse the course plan using the parser
            course_plan_json = self.course_parser.parse_course_plan(planner_content_str)
            
            if not course_plan_json:
                # Try one more time with a simpler request
                print("Attempting a retry with a simpler course plan request...")
                simpler_query = f"Create a simple course plan for '{subject}' with title '{title}' at {difficulty.value} difficulty. Make exactly 5 lessons. Return ONLY valid JSON with courseTitle, courseDescription, courseIcon, and lesson_outline_plan array."
                retry_response = planner.run(simpler_query)
                
                if retry_response and retry_response.content:
                    print(f"Retry response length: {len(retry_response.content)} characters")
                    course_plan_json = self.course_parser.parse_course_plan(retry_response.content)
                    if course_plan_json:
                        print("Successfully parsed retry response!")
                    else:
                        print("Could not parse retry response")
                        return None
                else:
                    print("Retry attempt also failed")
                    return None

            # Validate the course plan structure
            if not course_plan_json or "lesson_outline_plan" not in course_plan_json or not isinstance(course_plan_json["lesson_outline_plan"], list):
                print(f"Error: Invalid course plan structure from CoursePlannerAgent. Plan data: {course_plan_json}")
                return None

            num_planned_lessons = len(course_plan_json["lesson_outline_plan"])
            if not (5 <= num_planned_lessons <= 10):
                print(f"Warning: CoursePlannerAgent planned {num_planned_lessons} lessons, outside instructed range. Proceeding.")
            if num_planned_lessons == 0:
                print("Error: CoursePlannerAgent planned 0 lessons. Aborting.")
                return None
            
            # Validate lesson_outline_plan structure
            for i, item_dict in enumerate(course_plan_json["lesson_outline_plan"]):
                try:
                    LessonOutlineItem(**item_dict)
                except ValidationError as e_val:
                    print(f"Error: Invalid item in lesson_outline_plan at index {i}. Validation error details below.")
                    print(f"Problematic item_dict: {item_dict}")
                    print(f"Pydantic validation errors: {e_val.errors()}")
                    return None
            
            print(f"CoursePlannerAgent successfully generated a plan for {num_planned_lessons} lessons.")
            return course_plan_json

        except Exception as e:
            print(f"An exception occurred during CoursePlannerAgent execution: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _prepare_course_data(self, course_id: str, plan_data: Dict, subject: str, difficulty: CourseDifficulty) -> Dict[str, Any]:
        """Prepare course data for database insertion."""
        return {
            "id": course_id,
            "title": plan_data.get("courseTitle", "Untitled Course"),
            "subject": subject,
            "description": plan_data.get("courseDescription", f"A course on {subject}."),
            "difficulty": difficulty.value,
            "icon": plan_data.get("courseIcon"),
            "lesson_outline_plan": plan_data["lesson_outline_plan"],
            "generation_status": CourseStatus.DRAFT.value,
            "user_facing_status": UserCourseStatus.NOT_STARTED.value,
        }

    def _generate_lessons_async(self, course_id: str, plan_data: Dict, subject: str, difficulty: CourseDifficulty):
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
                        "user_facing_status": UserLessonStatus.NOT_STARTED.value
                    }
                    
                    try:
                        print(f"Creating placeholder for lesson: '{lesson_outline.planned_title}'")
                        placeholder_response = self.lesson_repo.create(lesson_placeholder_data)
                        if not placeholder_response or not placeholder_response.get('id'):
                            print(f"Error creating placeholder for lesson '{lesson_outline.planned_title}'.")
                            continue

                        lesson_id = placeholder_response['id']
                        print(f"Placeholder lesson created with ID: {lesson_id}")

                        # Update status to 'generating' before calling agent
                        self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATING.value})

                        print(f"Generating content for lesson: '{lesson_outline.planned_title}' (ID: {lesson_id})")
                        lesson_content_query = (
                            f"Lesson Title: {lesson_outline.planned_title}\\n"
                            f"Lesson Description: {lesson_outline.planned_description}\\n"
                            f"Overall Course Subject: {subject}\\n"
                            f"Overall Course Difficulty: {difficulty.value}"
                        )
                        
                        lesson_content_response = lesson_agent.run(lesson_content_query)
                        
                        if lesson_content_response and lesson_content_response.content:
                            # Extract links
                            extracted_links = extract_external_links(lesson_content_response.content)
                            
                            lesson_update_data = {
                                "content_md": lesson_content_response.content,
                                "external_links": json.dumps(extracted_links),
                                "generation_status": LessonStatus.COMPLETED.value
                            }
                            self.lesson_repo.update(lesson_id, lesson_update_data)
                            print(f"Content generated and saved for lesson ID: {lesson_id}")
                        else:
                            print(f"Failed to generate content for lesson ID: {lesson_id}. Error: {getattr(lesson_content_response, 'error', 'No content')}")
                            self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATION_FAILED.value})
                    
                    except Exception as e_lesson:
                        print(f"Exception during lesson processing for '{lesson_outline.planned_title}': {e_lesson}")
                        import traceback
                        traceback.print_exc()
                        if 'lesson_id' in locals():
                            self.lesson_repo.update(lesson_id, {"generation_status": LessonStatus.GENERATION_FAILED.value})
                        continue

                # Update course generation status to COMPLETED
                print(f"Lesson generation loop finished for course ID: {course_id}. Setting course generation_status to COMPLETED.")
                self.course_repo.update(course_id, {"generation_status": CourseStatus.COMPLETED.value})
                
            except Exception as e:
                print(f"Exception in background lesson generation for course ID {course_id}: {e}")
                import traceback
                traceback.print_exc()
                
                # Update course status to failed
                try:
                    self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATION_FAILED.value})
                except Exception as db_update_err:
                    print(f"Failed to update course status to GENERATION_FAILED after background exception: {db_update_err}")
        
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
                print(f"Course with ID {course_id} not found for retry.")
                return None
            
            course_subject = course_data.get('subject', 'General')
            lesson_outline_plan = course_data.get('lesson_outline_plan', [])
            
            if not lesson_outline_plan or not isinstance(lesson_outline_plan, list):
                print(f"Course {course_id} has no valid lesson_outline_plan. Cannot retry generation.")
                return None
            
            # Parse difficulty
            course_difficulty_str = course_data.get('difficulty', 'medium')
            try:
                course_difficulty_enum = CourseDifficulty(course_difficulty_str.lower())
            except ValueError:
                course_difficulty_enum = CourseDifficulty.MEDIUM
            
            print(f"Starting complete retry generation for course: {course_data.get('title')} (ID: {course_id})")
            print(f"Will recreate {len(lesson_outline_plan)} lessons from the course plan")
            
            # Delete all existing lessons for this course
            print(f"Deleting all existing lessons for course {course_id}")
            self.lesson_repo.delete_by_course_id(course_id)
            
            # Update course status to 'generating'
            self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATING.value})
            
            # Start background generation process
            self._generate_lessons_async(course_id, {"lesson_outline_plan": lesson_outline_plan}, course_subject, course_difficulty_enum)
            
            print(f"Background lesson generation started for course ID: {course_id}")
            
            # Return the current course state immediately (with no lessons since we deleted them)
            return self.get_course(course_id)
            
        except Exception as e:
            print(f"An unexpected exception occurred during course retry generation setup for ID {course_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update course status to failed if possible
            try:
                self.course_repo.update(course_id, {"generation_status": CourseStatus.GENERATION_FAILED.value})
            except Exception as db_update_err:
                print(f"Additionally, failed to update course status to GENERATION_FAILED after exception: {db_update_err}")
            
            return None