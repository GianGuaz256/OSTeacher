from fastapi import APIRouter, Depends, HTTPException, Path
from supabase import Client
from typing import Dict, Any

from ..database import get_db
from ..crud import regenerate_lesson as crud_regenerate_lesson # Alias to avoid name clash
from ..models import Lesson # For response model

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