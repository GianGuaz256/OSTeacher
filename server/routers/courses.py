from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from supabase import Client

from .. import crud, models, database

router = APIRouter(
    prefix="/courses",
    tags=["Courses"],
    responses={404: {"description": "Not found"}},
)

# Dependency to get the database client
def get_db_client():
    return database.get_db()

@router.post("/", status_code=status.HTTP_200_OK)
def create_new_course(request_data: models.CourseCreateRequest, db: Client = Depends(get_db_client)):
    """Create a new course by providing a title and subject, letting the AI agent team generate the rest."""
    created_course_full_data = crud.create_course_with_team(
        db=db, 
        initial_title=request_data.title,
        subject=request_data.subject,
        difficulty=request_data.difficulty
    )
    if created_course_full_data is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create course with agent team. Check server logs for details.")
    
    # No longer returning content, so the parsing and response model are not needed here.
    return # FastAPI will return a 200 OK with no body by default if status_code is set in decorator and function returns None

@router.get("/", response_model=List[models.Course])
def read_all_courses(skip: int = 0, limit: int = 100, db: Client = Depends(get_db_client)):
    """Retrieve all courses."""
    courses = crud.get_all_courses(db=db, skip=skip, limit=limit)
    # Map list of dictionaries to list of Pydantic models
    return [models.Course(**course) for course in courses]

@router.get("/{course_id}", response_model=models.Course)
def read_single_course(course_id: str, db: Client = Depends(get_db_client)):
    """Retrieve a single course by its ID."""
    db_course = crud.get_course(db=db, course_id=course_id)
    if db_course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return models.Course(**db_course)

@router.patch("/{course_id}", response_model=models.Course)
def update_existing_course(course_id: str, course_update_req: models.CourseUpdateRequest, db: Client = Depends(get_db_client)):
    """Update an existing course."""
    # Ensure to use the correct Pydantic model for the request body
    updated_course = crud.update_course(db=db, course_id=course_id, course_update_request=course_update_req)
    if updated_course is None:
        if crud.get_course(db=db, course_id=course_id) is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Course with id {course_id} not found")
        else:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update course {course_id}")

    return models.Course(**updated_course) 