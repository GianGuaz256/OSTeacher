from fastapi import APIRouter, Depends, HTTPException, Path
from supabase import Client
from typing import Dict, Any

from ..database import get_db
from ..crud import regenerate_lesson as crud_regenerate_lesson, update_lesson_user_status as crud_update_lesson_user_status # Alias and import new crud function
from ..models import Lesson, UserLessonStatus # For response model and request body

router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
)

@router.post(
    "/{lesson_id}/regenerate", 
    response_model=Lesson, # Use the Pydantic Lesson model for the response
    summary="Regenerate Content for a Specific Lesson",
    description="Triggers the regeneration of content for a lesson specified by its ID. The lesson must exist."
)
def route_regenerate_lesson(
    lesson_id: str = Path(..., title="The ID of the lesson to regenerate", min_length=36, max_length=36),
    db: Client = Depends(get_db)
) -> Dict[str, Any]: # Changed to Dict to match crud, FastAPI will handle Pydantic conversion
    """    Regenerates content for a specific lesson.\
    - **lesson_id**: UUID of the lesson.
    """
    print(f"Attempting to regenerate lesson with ID: {lesson_id}")
    updated_lesson_dict = crud_regenerate_lesson(db, lesson_id)
    if not updated_lesson_dict:
        raise HTTPException(
            status_code=404, 
            detail=f"Lesson with ID '{lesson_id}' not found or failed to regenerate."
        )
    
    # crud_regenerate_lesson returns a dict. FastAPI will convert this to Lesson Pydantic model.
    return updated_lesson_dict 

@router.put("/{lesson_id}/user-status", response_model=Lesson, summary="Update Lesson User-Facing Status")
async def route_set_lesson_user_status(
    status_update: UserLessonStatus, # Moved non-default argument before default ones
    lesson_id: str = Path(..., title="The ID of the lesson to update", min_length=36, max_length=36),
    db: Client = Depends(get_db)
):
    """
    Update the user-facing status of a specific lesson (e.g., not_started, in_progress, completed).
    This will also trigger a check to update the parent course's completion status.
    """
    updated_lesson_dict = crud_update_lesson_user_status(db, lesson_id, status_update)
    if not updated_lesson_dict:
        raise HTTPException(status_code=404, detail=f"Lesson {lesson_id} not found or status update failed")
    
    # crud_update_lesson_user_status already returns a dict suitable for Pydantic conversion by FastAPI
    # No need to re-parse with Lesson(**updated_lesson_dict) here if crud returns a validated dict
    # However, if crud returns an object that needs .model_dump(), ensure that is handled.
    # Assuming crud.update_lesson_user_status returns a dict that can be directly returned.
    return updated_lesson_dict 