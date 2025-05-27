from typing import Optional, Dict, Any, List
from supabase import Client
import json
import logging

from ..repositories.quiz_repository import QuizRepository
from ..repositories.lesson_repository import LessonRepository
from ..agents.quiz_generator_agent import QuizGeneratorAgent
from ..utils.retry_utils import is_retryable_error
from ..models import QuizCreateRequest, QuizUpdateRequest, QuizData, Quiz

logger = logging.getLogger(__name__)

class QuizService:
    """Service for quiz business logic."""
    
    def __init__(self, db: Client):
        self.db = db
        self.quiz_repository = QuizRepository(db)
        self.lesson_repository = LessonRepository(db)
        self.quiz_generator = QuizGeneratorAgent()
    
    def get_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Get a quiz by ID."""
        return self.quiz_repository.get_by_id(quiz_id)
    
    def get_quiz_by_lesson_id(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get a quiz by lesson ID."""
        return self.quiz_repository.get_by_lesson_id(lesson_id)
    
    def create_quiz_for_lesson(self, course_id: str, lesson_id: str, time_limit_seconds: int = 300, passing_score: int = 70) -> Optional[Dict[str, Any]]:
        """Create a quiz for a specific lesson."""
        try:
            # Check if lesson already has a quiz
            existing_quiz = self.quiz_repository.get_by_lesson_id(lesson_id)
            if existing_quiz:
                logger.info(f"Lesson {lesson_id} already has a quiz")
                return existing_quiz
            
            # Get lesson with course information
            lesson_data = self.lesson_repository.get_with_course_info(lesson_id)
            if not lesson_data:
                logger.error(f"Lesson {lesson_id} not found")
                return None
            
            # Generate quiz content
            quiz_data = self._generate_quiz_content(lesson_data)
            if not quiz_data:
                logger.error(f"Failed to generate quiz content for lesson {lesson_id}")
                return None
            
            # Create quiz record
            quiz_record = {
                "course_id": course_id,
                "lesson_id": lesson_id,
                "quiz_data": quiz_data,
                "time_limit_seconds": time_limit_seconds,
                "passing_score": passing_score,
                "is_final_quiz": False,
                "passed": None,  # Not attempted yet
                "is_active": True
            }
            
            created_quiz = self.quiz_repository.create(quiz_record)
            if created_quiz:
                # Update lesson to mark it as having a quiz
                self.lesson_repository.update(lesson_id, {"has_quiz": True})
                logger.info(f"Successfully created quiz for lesson {lesson_id}")
            
            return created_quiz
            
        except Exception as e:
            logger.error(f"Error creating quiz for lesson {lesson_id}: {e}")
            return None
    
    def create_final_quiz_for_course(self, course_id: str, time_limit_seconds: int = 600, passing_score: int = 80) -> Optional[Dict[str, Any]]:
        """Create a final quiz for the entire course."""
        try:
            # Check if course already has a final quiz
            existing_final_quiz = self.quiz_repository.get_final_quiz_by_course_id(course_id)
            if existing_final_quiz:
                logger.info(f"Course {course_id} already has a final quiz")
                return existing_final_quiz
            
            # Get course with all lessons
            course_data = self.lesson_repository.get_course_with_lessons(course_id)
            if not course_data:
                logger.error(f"Course {course_id} not found")
                return None
            
            # Generate final quiz content
            quiz_data = self._generate_final_quiz_content(course_data)
            if not quiz_data:
                logger.error(f"Failed to generate final quiz content for course {course_id}")
                return None
            
            # Create final quiz record
            quiz_record = {
                "course_id": course_id,
                "lesson_id": None,  # Final quiz is not tied to a specific lesson
                "quiz_data": quiz_data,
                "time_limit_seconds": time_limit_seconds,
                "passing_score": passing_score,
                "is_final_quiz": True,
                "passed": None,  # Not attempted yet
                "is_active": True
            }
            
            created_quiz = self.quiz_repository.create(quiz_record)
            if created_quiz:
                logger.info(f"Successfully created final quiz for course {course_id}")
            
            return created_quiz
            
        except Exception as e:
            logger.error(f"Error creating final quiz for course {course_id}: {e}")
            return None
    
    def get_quizzes_by_course_id(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all quizzes for a course."""
        return self.quiz_repository.get_by_course_id(course_id)
    
    def get_final_quiz_by_course_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get the final quiz for a course."""
        return self.quiz_repository.get_final_quiz_by_course_id(course_id)
    
    def update_quiz_passed_status(self, quiz_id: str, passed: bool) -> Optional[Dict[str, Any]]:
        """Update the passed status of a quiz."""
        try:
            return self.quiz_repository.update(quiz_id, {"passed": passed})
        except Exception as e:
            logger.error(f"Error updating quiz passed status {quiz_id}: {e}")
            return None
    
    def update_quiz(self, quiz_id: str, quiz_update_request: QuizUpdateRequest) -> Optional[Dict[str, Any]]:
        """Update an existing quiz."""
        try:
            update_data = {}
            
            if quiz_update_request.quiz_data is not None:
                update_data["quiz_data"] = quiz_update_request.quiz_data.dict()
            
            if quiz_update_request.time_limit_seconds is not None:
                update_data["time_limit_seconds"] = quiz_update_request.time_limit_seconds
            
            if quiz_update_request.passing_score is not None:
                update_data["passing_score"] = quiz_update_request.passing_score
            
            if quiz_update_request.is_active is not None:
                update_data["is_active"] = quiz_update_request.is_active
            
            if not update_data:
                return self.quiz_repository.get_by_id(quiz_id)
            
            return self.quiz_repository.update(quiz_id, update_data)
            
        except Exception as e:
            logger.error(f"Error updating quiz {quiz_id}: {e}")
            return None
    
    def delete_quiz(self, quiz_id: str) -> bool:
        """Delete a quiz and update the lesson."""
        try:
            # Get quiz to find lesson_id
            quiz_data = self.quiz_repository.get_by_id(quiz_id)
            if not quiz_data:
                return False
            
            lesson_id = quiz_data["lesson_id"]
            
            # Delete quiz
            success = self.quiz_repository.delete(quiz_id)
            if success:
                # Update lesson to mark it as not having a quiz
                self.lesson_repository.update(lesson_id, {"has_quiz": False})
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting quiz {quiz_id}: {e}")
            return False
    
    def regenerate_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Regenerate quiz content using AI."""
        try:
            # Get existing quiz
            quiz_data = self.quiz_repository.get_by_id(quiz_id)
            if not quiz_data:
                logger.error(f"Quiz {quiz_id} not found")
                return None
            
            lesson_id = quiz_data["lesson_id"]
            
            # Get lesson with course information
            lesson_data = self.lesson_repository.get_with_course_info(lesson_id)
            if not lesson_data:
                logger.error(f"Lesson {lesson_id} not found")
                return None
            
            # Generate new quiz content
            new_quiz_data = self._generate_quiz_content(lesson_data)
            if not new_quiz_data:
                logger.error(f"Failed to regenerate quiz content for lesson {lesson_id}")
                return None
            
            # Update quiz with new content
            update_data = {"quiz_data": new_quiz_data}
            return self.quiz_repository.update(quiz_id, update_data)
            
        except Exception as e:
            logger.error(f"Error regenerating quiz {quiz_id}: {e}")
            return None
    
    def _generate_quiz_content(self, lesson_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate quiz content using the QuizGeneratorAgent."""
        try:
            # Extract lesson information
            lesson_title = lesson_data.get("title", "")
            lesson_content = lesson_data.get("content_md", "")
            course_info = lesson_data.get("courses", {})
            course_subject = course_info.get("subject", "") if course_info else ""
            course_difficulty = course_info.get("difficulty", "") if course_info else ""
            
            if not lesson_content:
                logger.error(f"No content available for lesson: {lesson_title}")
                return None
            
            # Create query for the quiz generator
            query = f"""
            Create a quiz for the following lesson:
            
            Course Subject: {course_subject}
            Course Difficulty: {course_difficulty}
            Lesson Title: {lesson_title}
            
            Lesson Content:
            {lesson_content}
            
            Generate a comprehensive quiz that tests understanding of the key concepts covered in this lesson.
            """
            
            # Generate quiz using AI agent with retry logic
            logger.info(f"Generating quiz content for lesson: {lesson_title}")
            response = self.quiz_generator.run(query)
            
            # Handle error response from agent
            if hasattr(response, 'error') and response.error:
                error_msg = str(response.error)
                if is_retryable_error(Exception(response.error)):
                    logger.error(f"Quiz generation failed due to connection issues: {error_msg}")
                else:
                    logger.error(f"Quiz generation failed: {error_msg}")
                return None
            
            if not response or not hasattr(response, 'content') or not response.content:
                logger.error("No response from quiz generator")
                return None
            
            # Parse the JSON response
            try:
                quiz_json = json.loads(response.content)
                logger.info(f"Successfully generated quiz for lesson: {lesson_title}")
                return quiz_json
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse quiz JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating quiz content: {e}")
            return None
    
    def get_quizzes_for_lessons(self, lesson_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quizzes for multiple lessons."""
        return self.quiz_repository.get_by_lesson_ids(lesson_ids)
    
    def _generate_final_quiz_content(self, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate final quiz content for the entire course using the QuizGeneratorAgent."""
        try:
            # Extract course information
            course_title = course_data.get("title", "")
            course_subject = course_data.get("subject", "")
            course_description = course_data.get("description", "")
            course_difficulty = course_data.get("difficulty", "")
            lessons = course_data.get("lessons", [])
            
            if not lessons:
                logger.error(f"No lessons available for course: {course_title}")
                return None
            
            # Compile all lesson content for comprehensive quiz
            all_lesson_content = []
            for lesson in lessons:
                lesson_title = lesson.get("title", "")
                lesson_content = lesson.get("content_md", "")
                if lesson_content:
                    all_lesson_content.append(f"**{lesson_title}**\n{lesson_content}")
            
            combined_content = "\n\n---\n\n".join(all_lesson_content)
            
            # Create query for the final quiz generator
            query = f"""
            Create a comprehensive final quiz for the following course:
            
            Course Title: {course_title}
            Course Subject: {course_subject}
            Course Description: {course_description}
            Course Difficulty: {course_difficulty}
            
            This is a FINAL QUIZ that should test the student's overall understanding and competencies acquired throughout the entire course.
            
            Course Content (All Lessons):
            {combined_content}
            
            Generate a comprehensive final quiz with 8-12 questions that:
            1. Tests understanding of key concepts from across ALL lessons
            2. Includes questions that require synthesis of knowledge from multiple lessons
            3. Covers the most important learning objectives of the course
            4. Has a mix of difficulty levels appropriate for a final assessment
            5. Validates that the student has acquired the core competencies of the course
            
            Make this quiz more challenging than individual lesson quizzes as it's the final assessment.
            """
            
            # Generate quiz using AI agent with retry logic
            logger.info(f"Generating final quiz content for course: {course_title}")
            response = self.quiz_generator.run(query)
            
            # Handle error response from agent
            if hasattr(response, 'error') and response.error:
                error_msg = str(response.error)
                if is_retryable_error(Exception(response.error)):
                    logger.error(f"Final quiz generation failed due to connection issues: {error_msg}")
                else:
                    logger.error(f"Final quiz generation failed: {error_msg}")
                return None
            
            if not response or not hasattr(response, 'content') or not response.content:
                logger.error("No response from quiz generator for final quiz")
                return None
            
            # Parse the JSON response
            try:
                quiz_json = json.loads(response.content)
                # Update the title to indicate it's a final quiz
                if "quizTitle" in quiz_json:
                    quiz_json["quizTitle"] = f"{course_title} - Final Quiz"
                logger.info(f"Successfully generated final quiz for course: {course_title}")
                return quiz_json
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse final quiz JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating final quiz content: {e}")
            return None 