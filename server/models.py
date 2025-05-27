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

class CourseField(str, Enum):
    """Predefined fields of study for courses."""
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    MATHEMATICS = "mathematics"
    BUSINESS = "business"
    ARTS = "arts"
    LANGUAGE = "language"
    HEALTH = "health"
    HISTORY = "history"
    PHILOSOPHY = "philosophy"
    ENGINEERING = "engineering"
    DESIGN = "design"
    MUSIC = "music"
    LITERATURE = "literature"
    PSYCHOLOGY = "psychology"
    ECONOMICS = "economics"

# Quiz-related models
class QuizQuestion(BaseModel):
    question: str
    questionType: str = "text"  # "text" or "photo"
    questionPic: Optional[str] = None
    answerSelectionType: str = "single"  # "single" or "multiple"
    answers: List[str]
    correctAnswer: str  # For single answer: "1", "2", etc. For multiple: ["1", "2"]
    messageForCorrectAnswer: str = "Correct answer. Good job."
    messageForIncorrectAnswer: str = "Incorrect answer. Please try again."
    explanation: Optional[str] = None
    point: str = "10"

class QuizData(BaseModel):
    quizTitle: str
    quizSynopsis: str
    progressBarColor: str = "#9de1f6"
    nrOfQuestions: str
    questions: List[QuizQuestion]

class Quiz(BaseModel):
    id: Optional[str] = None
    course_id: str  # Added course_id field
    lesson_id: Optional[str] = None  # Made optional for final course quizzes
    quiz_data: QuizData
    time_limit_seconds: int = 300  # 5 minutes default
    passing_score: int = 70  # Percentage required to pass
    is_active: bool = True
    is_final_quiz: bool = False  # Flag to indicate if this is the final course quiz
    passed: Optional[bool] = None  # Track if user passed the quiz
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class QuizCreateRequest(BaseModel):
    course_id: str  # Added course_id field
    lesson_id: Optional[str] = None  # Made optional for final course quizzes
    time_limit_seconds: int = 300
    passing_score: int = 70
    is_final_quiz: bool = False

class QuizUpdateRequest(BaseModel):
    quiz_data: Optional[QuizData] = None
    time_limit_seconds: Optional[int] = None
    passing_score: Optional[int] = None
    is_active: Optional[bool] = None
    passed: Optional[bool] = None  # Allow updating passed status

class QuizStatusUpdateRequest(BaseModel):
    passed: bool

# New model for items in the lesson_outline_plan
class LessonOutlineItem(BaseModel):
    order: int
    planned_title: str
    planned_description: Optional[str] = None
    has_quiz: bool = False  # New field to indicate if lesson should have a quiz
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
    has_quiz: bool = False  # New field to indicate if lesson has a quiz
    quiz: Optional[Quiz] = None  # Optional quiz data when fetched with quiz

class Course(BaseModel):
    id: Optional[str] = None 
    title: str
    subject: str
    description: str
    icon: Optional[str] = None
    difficulty: Optional[CourseDifficulty] = None
    field: Optional[CourseField] = None  # New field for field of study
    has_quizzes: bool = False  # New field to indicate if course has quizzes
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
    has_quizzes: bool = False  # Added has_quizzes flag
    # lessons list is removed from here, as they are not created directly with the course object in one go.
    # The creation process will generate an outline first.

class CourseUpdateRequest(BaseModel): # Renamed from CourseUpdate for clarity
    title: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[UserCourseStatus] = None # Changed from CourseStatus to UserCourseStatus
    level: Optional[CourseLevel] = None
    icon: Optional[str] = None
    field: Optional[CourseField] = None  # New field for field of study
    lesson_outline_plan: Optional[List[LessonOutlineItem]] = None # Allow updating the plan
    # lessons: Optional[List[Lesson]] = None # Removed: Lesson content updates will be handled differently (e.g., regeneration or more granular lesson endpoints)

# Response model for course creation
class CourseCreationResponse(BaseModel):
    id: str
    message: str
    icon_suggestion: Optional[str] = None
    course_data: Optional[Course] = None # Return the full course object 