from typing import List, Optional, Dict, Any
from supabase import Client
from ..config.settings import settings
import json

class CourseRepository:
    """Repository for course database operations."""
    
    def __init__(self, db: Client):
        self.db = db
        self.table = settings.COURSE_TABLE
    
    def create(self, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new course in the database."""
        try:
            response = self.db.table(self.table).insert(course_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating course: {e}")
            return None
    
    def get_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get a course by ID."""
        try:
            course_response = self.db.table(self.table).select("*").eq("id", course_id).single().execute()
            
            if not course_response.data:
                return None
            
            course_data = course_response.data
            
            # Ensure lesson_outline_plan is parsed if it's a string (though Supabase client usually handles JSONB)
            if isinstance(course_data.get('lesson_outline_plan'), str):
                try:
                    course_data['lesson_outline_plan'] = json.loads(course_data['lesson_outline_plan'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse lesson_outline_plan for course {course_id}")
                    course_data['lesson_outline_plan'] = None # Or handle as an error
            
            # Map db 'user_facing_status' to pydantic 'status' for the course
            if 'user_facing_status' in course_data:
                course_data['status'] = course_data.pop('user_facing_status')

            return course_data
            
        except Exception as e:
            print(f"Error fetching course {course_id}: {e}")
            return None
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all courses with pagination."""
        try:
            courses_response = self.db.table(self.table).select("*").range(skip, skip + limit - 1).execute()
            
            if not courses_response.data:
                return []
                
            courses_data = courses_response.data
            
            for course in courses_data:
                # Ensure lesson_outline_plan is parsed
                if isinstance(course.get('lesson_outline_plan'), str):
                    try:
                        course['lesson_outline_plan'] = json.loads(course['lesson_outline_plan'])
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse lesson_outline_plan for course {course.get('id')}")
                        course['lesson_outline_plan'] = None
                # Map db 'user_facing_status' to pydantic 'status' for the course
                if 'user_facing_status' in course:
                    course['status'] = course.pop('user_facing_status')
                    
            return courses_data
            
        except Exception as e:
            print(f"Error fetching courses: {e}")
            return []
    
    def update(self, course_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a course."""
        try:
            response = self.db.table(self.table).update(update_data).eq("id", course_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating course {course_id}: {e}")
            return None
    
    def exists(self, course_id: str) -> bool:
        """Check if a course exists."""
        try:
            response = self.db.table(self.table).select("id").eq("id", course_id).maybe_single().execute()
            return response.data is not None
        except Exception as e:
            print(f"Error checking course existence {course_id}: {e}")
            return False 