from typing import List, Optional, Dict, Any
from supabase import Client
from ..config.settings import settings
import json

class QuizRepository:
    """Repository for quiz database operations."""
    
    def __init__(self, db: Client):
        self.db = db
        self.table = settings.QUIZZES_TABLE
    
    def create(self, quiz_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new quiz in the database."""
        try:
            response = self.db.table(self.table).insert(quiz_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating quiz: {e}")
            return None
    
    def get_by_id(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Get a quiz by ID."""
        try:
            response = self.db.table(self.table).select("*").eq("id", quiz_id).maybe_single().execute()
            
            if not response.data:
                return None
            
            quiz_data = response.data
            
            # Ensure quiz_data is parsed if it's a string (though Supabase client usually handles JSONB)
            if isinstance(quiz_data.get('quiz_data'), str):
                try:
                    quiz_data['quiz_data'] = json.loads(quiz_data['quiz_data'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse quiz_data for quiz {quiz_id}")
                    quiz_data['quiz_data'] = None
            
            return quiz_data
            
        except Exception as e:
            print(f"Error fetching quiz {quiz_id}: {e}")
            return None
    
    def get_by_lesson_id(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get a quiz by lesson ID."""
        try:
            response = self.db.table(self.table).select("*").eq("lesson_id", lesson_id).eq("is_active", True).maybe_single().execute()
            
            if not response.data:
                return None
            
            quiz_data = response.data
            
            # Ensure quiz_data is parsed if it's a string
            if isinstance(quiz_data.get('quiz_data'), str):
                try:
                    quiz_data['quiz_data'] = json.loads(quiz_data['quiz_data'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse quiz_data for lesson {lesson_id}")
                    quiz_data['quiz_data'] = None
            
            return quiz_data
            
        except Exception as e:
            print(f"Error fetching quiz for lesson {lesson_id}: {e}")
            return None
    
    def get_by_lesson_ids(self, lesson_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quizzes for multiple lessons."""
        try:
            if not lesson_ids:
                return {}
            
            response = self.db.table(self.table).select("*").in_("lesson_id", lesson_ids).eq("is_active", True).execute()
            
            quizzes_by_lesson_id: Dict[str, Dict[str, Any]] = {}
            if response.data:
                for quiz_dict in response.data:
                    lesson_id_for_quiz = quiz_dict['lesson_id']
                    
                    # Ensure quiz_data is parsed
                    if isinstance(quiz_dict.get('quiz_data'), str):
                        try:
                            quiz_dict['quiz_data'] = json.loads(quiz_dict['quiz_data'])
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse quiz_data for lesson {lesson_id_for_quiz}")
                            quiz_dict['quiz_data'] = None
                    
                    quizzes_by_lesson_id[lesson_id_for_quiz] = quiz_dict
            
            return quizzes_by_lesson_id
            
        except Exception as e:
            print(f"Error fetching quizzes for multiple lessons: {e}")
            return {}
    
    def update(self, quiz_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a quiz."""
        try:
            response = self.db.table(self.table).update(update_data).eq("id", quiz_id).execute()
            
            if response.data and len(response.data) > 0:
                updated_quiz_data = response.data[0]
                
                # Ensure quiz_data is parsed
                if isinstance(updated_quiz_data.get('quiz_data'), str):
                    try:
                        updated_quiz_data['quiz_data'] = json.loads(updated_quiz_data['quiz_data'])
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse quiz_data for quiz {quiz_id}")
                        updated_quiz_data['quiz_data'] = None
                
                return updated_quiz_data
            return None
            
        except Exception as e:
            print(f"Error updating quiz {quiz_id}: {e}")
            return None
    
    def delete(self, quiz_id: str) -> bool:
        """Delete a quiz."""
        try:
            self.db.table(self.table).delete().eq("id", quiz_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting quiz {quiz_id}: {e}")
            return False
    
    def delete_by_lesson_id(self, lesson_id: str) -> bool:
        """Delete all quizzes for a lesson."""
        try:
            self.db.table(self.table).delete().eq("lesson_id", lesson_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting quizzes for lesson {lesson_id}: {e}")
            return False
    
    def exists(self, quiz_id: str) -> bool:
        """Check if a quiz exists."""
        try:
            response = self.db.table(self.table).select("id").eq("id", quiz_id).maybe_single().execute()
            return response.data is not None
        except Exception as e:
            print(f"Error checking quiz existence {quiz_id}: {e}")
            return False
    
    def lesson_has_quiz(self, lesson_id: str) -> bool:
        """Check if a lesson has an active quiz."""
        try:
            response = self.db.table(self.table).select("id").eq("lesson_id", lesson_id).eq("is_active", True).maybe_single().execute()
            return response.data is not None
        except Exception as e:
            print(f"Error checking if lesson has quiz {lesson_id}: {e}")
            return False
    
    def get_by_course_id(self, course_id: str) -> List[Dict[str, Any]]:
        """Get all quizzes for a course."""
        try:
            response = self.db.table(self.table).select("*").eq("course_id", course_id).eq("is_active", True).execute()
            
            quizzes = []
            if response.data:
                for quiz_dict in response.data:
                    # Ensure quiz_data is parsed
                    if isinstance(quiz_dict.get('quiz_data'), str):
                        try:
                            quiz_dict['quiz_data'] = json.loads(quiz_dict['quiz_data'])
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse quiz_data for quiz {quiz_dict.get('id')}")
                            quiz_dict['quiz_data'] = None
                    
                    quizzes.append(quiz_dict)
            
            return quizzes
            
        except Exception as e:
            print(f"Error fetching quizzes for course {course_id}: {e}")
            return []
    
    def get_final_quiz_by_course_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Get the final quiz for a course."""
        try:
            response = self.db.table(self.table).select("*").eq("course_id", course_id).eq("is_final_quiz", True).eq("is_active", True).maybe_single().execute()
            
            if not response.data:
                return None
            
            quiz_data = response.data
            
            # Ensure quiz_data is parsed
            if isinstance(quiz_data.get('quiz_data'), str):
                try:
                    quiz_data['quiz_data'] = json.loads(quiz_data['quiz_data'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse quiz_data for final quiz of course {course_id}")
                    quiz_data['quiz_data'] = None
            
            return quiz_data
            
        except Exception as e:
            print(f"Error fetching final quiz for course {course_id}: {e}")
            return None 