"""
New CRUD interface that maintains backward compatibility while using the refactored architecture.
This file provides the same function signatures as the original crud.py but delegates to services.
"""

from typing import List, Optional, Dict, Any
from supabase import Client

from .services.course_service import CourseService
from .services.lesson_service import LessonService
from .models import CourseUpdateRequest, CourseDifficulty, UserLessonStatus

# Maintain the same function signatures as the original crud.py

def get_course(db: Client, course_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single course by its ID, including its lessons."""
    course_service = CourseService(db)
    return course_service.get_course(course_id)

def get_all_courses(db: Client, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves all courses with pagination, including their lessons."""
    course_service = CourseService(db)
    return course_service.get_all_courses(skip, limit)

def update_course(db: Client, course_id: str, course_update_request: CourseUpdateRequest) -> Optional[Dict[str, Any]]:
    """Updates an existing course by its ID."""
    course_service = CourseService(db)
    return course_service.update_course(course_id, course_update_request)

def create_course_with_team(db: Client, initial_title: str, subject: str, difficulty: CourseDifficulty) -> Optional[Dict[str, Any]]:
    """
    Generates a course using an Agent Team (Planner and Lesson Content agents),
    saves the course outline, then incrementally creates and generates content for each lesson.
    """
    course_service = CourseService(db)
    return course_service.create_course_with_team(initial_title, subject, difficulty)

def retry_course_generation(db: Client, course_id: str) -> Optional[Dict[str, Any]]:
    """
    Retries course generation by deleting all existing lessons and recreating them from scratch.
    Uses the course's lesson_outline_plan JSON to recreate all lessons.
    """
    course_service = CourseService(db)
    return course_service.retry_course_generation(course_id)

def regenerate_lesson(db: Client, lesson_id: str) -> Optional[Dict[str, Any]]:
    """Regenerates the content for a specific lesson using the LessonContentAgent."""
    lesson_service = LessonService(db)
    return lesson_service.regenerate_lesson(lesson_id)

def update_lesson_user_status(db: Client, lesson_id: str, new_user_status: UserLessonStatus) -> Optional[Dict[str, Any]]:
    """Updates the user-facing status of a lesson and then checks course completion."""
    lesson_service = LessonService(db)
    return lesson_service.update_lesson_user_status(lesson_id, new_user_status)

# Legacy functions that are no longer used but kept for backward compatibility
def create_course(db: Client, title: str, subject: str, difficulty: str) -> Optional[dict]:
    """
    Legacy function - use create_course_with_team instead.
    Maintained for backward compatibility.
    """
    try:
        difficulty_enum = CourseDifficulty(difficulty.lower())
    except ValueError:
        difficulty_enum = CourseDifficulty.MEDIUM
    
    course_service = CourseService(db)
    return course_service.create_course_with_team(title, subject, difficulty_enum) 