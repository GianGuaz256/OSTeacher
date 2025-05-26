from typing import List, Optional, Dict, Any
from supabase import Client
from ..config.settings import settings
from ..utils.helpers import parse_lesson_external_links
import json

class LessonRepository:
    """Repository for lesson database operations."""
    
    def __init__(self, db: Client):
        self.db = db
        self.table = settings.LESSONS_TABLE
    
    def create(self, lesson_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new lesson in the database."""
        try:
            response = self.db.table(self.table).insert(lesson_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating lesson: {e}")
            return None
    
    def get_by_id(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get a lesson by ID."""
        try:
            response = self.db.table(self.table).select("*").eq("id", lesson_id).maybe_single().execute()
            
            if not response.data:
                return None
            
            lesson_data = response.data
            
            # Map db 'user_facing_status' to pydantic 'status'
            if 'user_facing_status' in lesson_data:
                lesson_data['status'] = lesson_data.pop('user_facing_status')
            
            return parse_lesson_external_links(lesson_data)
            
        except Exception as e:
            print(f"Error fetching lesson {lesson_id}: {e}")
            return None
    
    def get_by_course_id(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all lessons for a course."""
        try:
            lessons_response = self.db.table(self.table).select("*").eq("course_id", course_id).order("order_in_course", desc=False).execute()
            
            processed_lessons = []
            if lessons_response.data:
                for lesson_dict in lessons_response.data:
                    # Map db 'user_facing_status' to pydantic 'status'
                    if 'user_facing_status' in lesson_dict:
                        lesson_dict['status'] = lesson_dict.pop('user_facing_status')
                    
                    processed_lessons.append(parse_lesson_external_links(lesson_dict))
            
            return processed_lessons
            
        except Exception as e:
            print(f"Error fetching lessons for course {course_id}: {e}")
            return []
    
    def get_by_course_ids(self, course_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get all lessons for multiple courses."""
        try:
            if not course_ids:
                return {}
            
            all_lessons_response = self.db.table(self.table).select("*").in_("course_id", course_ids).order("order_in_course", desc=False).execute()
            
            lessons_by_course_id: Dict[str, List[Dict[str, Any]]] = {}
            if all_lessons_response.data:
                for lesson_dict in all_lessons_response.data:
                    course_id_for_lesson = lesson_dict['course_id']
                    if course_id_for_lesson not in lessons_by_course_id:
                        lessons_by_course_id[course_id_for_lesson] = []
                    
                    # Map db 'user_facing_status' to pydantic 'status'
                    if 'user_facing_status' in lesson_dict:
                        lesson_dict['status'] = lesson_dict.pop('user_facing_status')
                    
                    lessons_by_course_id[course_id_for_lesson].append(parse_lesson_external_links(lesson_dict))
            
            return lessons_by_course_id
            
        except Exception as e:
            print(f"Error fetching lessons for multiple courses: {e}")
            return {}
    
    def update(self, lesson_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a lesson."""
        try:
            response = self.db.table(self.table).update(update_data).eq("id", lesson_id).execute()
            
            if response.data and len(response.data) > 0:
                updated_lesson_data = response.data[0]
                # Map db 'user_facing_status' to pydantic 'status' for the returned lesson object
                if 'user_facing_status' in updated_lesson_data:
                    updated_lesson_data['status'] = updated_lesson_data.pop('user_facing_status')
                
                return parse_lesson_external_links(updated_lesson_data)
            return None
            
        except Exception as e:
            print(f"Error updating lesson {lesson_id}: {e}")
            return None
    
    def delete_by_course_id(self, course_id: str) -> bool:
        """Delete all lessons for a course."""
        try:
            self.db.table(self.table).delete().eq("course_id", course_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting lessons for course {course_id}: {e}")
            return False
    
    def get_with_course_info(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get a lesson with its course information."""
        try:
            # Ensure 'courses' is the correct relationship name for the join.
            lesson_response = self.db.table(self.table).select("*, courses(id, subject, difficulty)").eq("id", lesson_id).maybe_single().execute()
            
            if not lesson_response.data:
                return None
            
            lesson_data = lesson_response.data
            
            # Map db 'user_facing_status' to pydantic 'status'
            if 'user_facing_status' in lesson_data:
                lesson_data['status'] = lesson_data.pop('user_facing_status')
            
            return parse_lesson_external_links(lesson_data)
            
        except Exception as e:
            print(f"Error fetching lesson with course info {lesson_id}: {e}")
            return None 