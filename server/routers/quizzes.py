from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from supabase import Client

from ..database import get_db
from ..services.quiz_service import QuizService
from ..models import QuizCreateRequest, QuizUpdateRequest, QuizStatusUpdateRequest

router = APIRouter(prefix="/quizzes", tags=["quizzes"])

@router.post("/lessons/{lesson_id}/quiz")
def create_quiz_for_lesson(
    lesson_id: str,
    quiz_request: QuizCreateRequest,
    db: Client = Depends(get_db)
):
    """Create a quiz for a specific lesson."""
    quiz_service = QuizService(db)
    
    quiz = quiz_service.create_quiz_for_lesson(
        quiz_request.course_id, 
        lesson_id, 
        quiz_request.time_limit_seconds, 
        quiz_request.passing_score
    )
    
    if not quiz:
        raise HTTPException(status_code=400, detail="Failed to create quiz for lesson")
    
    return quiz

@router.get("/lessons/{lesson_id}/quiz")
def get_quiz_by_lesson_id(lesson_id: str, db: Client = Depends(get_db)):
    """Get the quiz for a specific lesson."""
    quiz_service = QuizService(db)
    quiz = quiz_service.get_quiz_by_lesson_id(lesson_id)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found for this lesson")
    
    return quiz

@router.get("/{quiz_id}")
def get_quiz(quiz_id: str, db: Client = Depends(get_db)):
    """Get a quiz by ID."""
    quiz_service = QuizService(db)
    quiz = quiz_service.get_quiz(quiz_id)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return quiz

@router.put("/{quiz_id}")
def update_quiz(
    quiz_id: str,
    quiz_update: QuizUpdateRequest,
    db: Client = Depends(get_db)
):
    """Update a quiz."""
    quiz_service = QuizService(db)
    updated_quiz = quiz_service.update_quiz(quiz_id, quiz_update)
    
    if not updated_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found or update failed")
    
    return updated_quiz

@router.delete("/{quiz_id}")
def delete_quiz(quiz_id: str, db: Client = Depends(get_db)):
    """Delete a quiz."""
    quiz_service = QuizService(db)
    success = quiz_service.delete_quiz(quiz_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Quiz not found or deletion failed")
    
    return {"message": "Quiz deleted successfully"}

@router.post("/{quiz_id}/regenerate")
def regenerate_quiz(quiz_id: str, db: Client = Depends(get_db)):
    """Regenerate quiz content using AI."""
    quiz_service = QuizService(db)
    regenerated_quiz = quiz_service.regenerate_quiz(quiz_id)
    
    if not regenerated_quiz:
        raise HTTPException(status_code=400, detail="Failed to regenerate quiz")
    
    return regenerated_quiz

@router.post("/courses/{course_id}/final-quiz")
def create_final_quiz_for_course(
    course_id: str,
    quiz_request: Optional[QuizCreateRequest] = None,
    db: Client = Depends(get_db)
):
    """Create a final quiz for a course."""
    quiz_service = QuizService(db)
    
    # Use default values if no request body provided
    time_limit = quiz_request.time_limit_seconds if quiz_request else 600  # 10 minutes for final quiz
    passing_score = quiz_request.passing_score if quiz_request else 80  # Higher passing score for final quiz
    
    quiz = quiz_service.create_final_quiz_for_course(course_id, time_limit, passing_score)
    
    if not quiz:
        raise HTTPException(status_code=400, detail="Failed to create final quiz for course")
    
    return quiz

@router.get("/courses/{course_id}/quizzes")
def get_quizzes_by_course_id(course_id: str, db: Client = Depends(get_db)):
    """Get all quizzes for a course."""
    quiz_service = QuizService(db)
    quizzes = quiz_service.get_quizzes_by_course_id(course_id)
    return quizzes

@router.get("/courses/{course_id}/final-quiz")
def get_final_quiz_by_course_id(course_id: str, db: Client = Depends(get_db)):
    """Get the final quiz for a course."""
    quiz_service = QuizService(db)
    quiz = quiz_service.get_final_quiz_by_course_id(course_id)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Final quiz not found for this course")
    
    return quiz

@router.put("/{quiz_id}/status")
def update_quiz_status(
    quiz_id: str,
    status_update: QuizStatusUpdateRequest,
    db: Client = Depends(get_db)
):
    """Update the passed status of a quiz."""
    quiz_service = QuizService(db)
    updated_quiz = quiz_service.update_quiz_passed_status(quiz_id, status_update.passed)
    
    if not updated_quiz:
        raise HTTPException(status_code=404, detail="Quiz not found or update failed")
    
    return updated_quiz 