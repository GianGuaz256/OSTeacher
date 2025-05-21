from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum
import uuid
from datetime import datetime

class LessonStatus(str, Enum):
    PLANNED = "planned"
    GENERATING = "generating"
    COMPLETED = "completed"
    GENERATION_FAILED = "generation_failed"
    NEEDS_REVIEW = "needs_review"
    PENDING = "pending" # Keep for backward compatibility if needed, or phase out
    # Add any specific generation statuses if different from user-facing ones
    # For now, we'll assume they can share the same enum, but this might change.

class UserLessonStatus(str, Enum): # New Enum for user-facing lesson status
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class CourseStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    GENERATING = "generating" # Added for course generation status
    COMPLETED = "completed" # Added for course completion status
    GENERATION_FAILED = "generation_failed" # Added for course generation failure

class UserCourseStatus(str, Enum): # New Enum for user-facing course status
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class CourseLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class CourseDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# New model for items in the lesson_outline_plan
class LessonOutlineItem(BaseModel):
    order: int
    planned_title: str
    planned_description: Optional[str] = None
    # You might add a unique ID here if planner generates one, or rely on order for initial creation

class Lesson(BaseModel):
    id: Optional[str] = None # Will be set when fetched from DB
    course_id: Optional[str] = None # Will be set when fetched/created
    title: str
    planned_description: Optional[str] = None # New field
    content_md: Optional[str] = None # Can be None while generating or if generation fails
    external_links: List[str] = Field(default_factory=list)
    generation_status: LessonStatus = LessonStatus.PLANNED # New field for generation process
    status: UserLessonStatus = UserLessonStatus.NOT_STARTED # User-facing status
    order_in_course: Optional[int] = None # Will be set

class Course(BaseModel):
    id: Optional[str] = None 
    title: str
    subject: str
    description: str
    icon: Optional[str] = None
    difficulty: Optional[CourseDifficulty] = None
    lesson_outline_plan: Optional[List[LessonOutlineItem]] = None # New field to store the plan
    lessons: List[Lesson] = Field(default_factory=list) # This will be populated from the separate 'lessons' table
    # The 'lessons' field above is for API response. It's not directly stored in 'courses' table as JSON blob anymore.
    generation_status: CourseStatus = CourseStatus.DRAFT # New field for course generation status
    status: UserCourseStatus = UserCourseStatus.NOT_STARTED # Default user-facing status if not provided
    level: Optional[CourseLevel] = None # Added from CourseUpdate
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CourseCreateRequest(BaseModel):
    title: str
    subject: str
    difficulty: CourseDifficulty
    # lessons list is removed from here, as they are not created directly with the course object in one go.
    # The creation process will generate an outline first.

class CourseUpdateRequest(BaseModel): # Renamed from CourseUpdate for clarity
    title: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[UserCourseStatus] = None # Changed from CourseStatus to UserCourseStatus
    level: Optional[CourseLevel] = None
    icon: Optional[str] = None
    lesson_outline_plan: Optional[List[LessonOutlineItem]] = None # Allow updating the plan
    # lessons: Optional[List[Lesson]] = None # Removed: Lesson content updates will be handled differently (e.g., regeneration or more granular lesson endpoints)

# Response model for course creation
class CourseCreationResponse(BaseModel):
    id: str
    message: str
    icon_suggestion: Optional[str] = None
    course_data: Optional[Course] = None # Return the full course object 