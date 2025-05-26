export enum LessonStatus {
  PLANNED = "planned",
  GENERATING = "generating",
  COMPLETED = "completed",
  GENERATION_FAILED = "generation_failed",
  NEEDS_REVIEW = "needs_review",
  PENDING = "pending", // Retained for now, consider phasing out if not used
}

export enum UserLessonStatus { // New Enum for user-facing lesson status
  NOT_STARTED = "not_started",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
}

export enum CourseStatus {
  DRAFT = "draft",
  PUBLISHED = "published",
  ARCHIVED = "archived",
  GENERATING = "generating", // Added for course generation status
  COMPLETED = "completed", // Added for course completion status
  GENERATION_FAILED = "generation_failed", // Added for course generation failure
}

export enum UserCourseStatus { // New Enum for user-facing course status
  NOT_STARTED = "not_started",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
}

export enum CourseLevel {
  BEGINNER = "beginner",
  INTERMEDIATE = "intermediate",
  ADVANCED = "advanced",
}

export enum CourseDifficulty {
  EASY = "easy",
  MEDIUM = "medium",
  HARD = "hard",
}

export enum CourseField {
  TECHNOLOGY = "technology",
  SCIENCE = "science",
  MATHEMATICS = "mathematics",
  BUSINESS = "business",
  ARTS = "arts",
  LANGUAGE = "language",
  HEALTH = "health",
  HISTORY = "history",
  PHILOSOPHY = "philosophy",
  ENGINEERING = "engineering",
  DESIGN = "design",
  MUSIC = "music",
  LITERATURE = "literature",
  PSYCHOLOGY = "psychology",
  ECONOMICS = "economics",
}

// Helper function to get emoji for each field
export const getFieldEmoji = (field: CourseField | string | undefined): string => {
  if (!field) return '';
  
  const fieldEmojiMap: Record<string, string> = {
    [CourseField.TECHNOLOGY]: '💻',
    [CourseField.SCIENCE]: '🔬',
    [CourseField.MATHEMATICS]: '📊',
    [CourseField.BUSINESS]: '💼',
    [CourseField.ARTS]: '🎨',
    [CourseField.LANGUAGE]: '🗣️',
    [CourseField.HEALTH]: '🏥',
    [CourseField.HISTORY]: '📚',
    [CourseField.PHILOSOPHY]: '🤔',
    [CourseField.ENGINEERING]: '⚙️',
    [CourseField.DESIGN]: '✨',
    [CourseField.MUSIC]: '🎵',
    [CourseField.LITERATURE]: '📖',
    [CourseField.PSYCHOLOGY]: '🧠',
    [CourseField.ECONOMICS]: '📈',
  };
  
  return fieldEmojiMap[field] || '';
};

// Helper function to get display name for field
export const getFieldDisplayName = (field: CourseField | string | undefined): string => {
  if (!field) return '';
  
  const fieldMap: Record<string, string> = {
    [CourseField.TECHNOLOGY]: 'Technology',
    [CourseField.SCIENCE]: 'Science',
    [CourseField.MATHEMATICS]: 'Mathematics',
    [CourseField.BUSINESS]: 'Business',
    [CourseField.ARTS]: 'Arts',
    [CourseField.LANGUAGE]: 'Language',
    [CourseField.HEALTH]: 'Health',
    [CourseField.HISTORY]: 'History',
    [CourseField.PHILOSOPHY]: 'Philosophy',
    [CourseField.ENGINEERING]: 'Engineering',
    [CourseField.DESIGN]: 'Design',
    [CourseField.MUSIC]: 'Music',
    [CourseField.LITERATURE]: 'Literature',
    [CourseField.PSYCHOLOGY]: 'Psychology',
    [CourseField.ECONOMICS]: 'Economics',
  };
  
  return fieldMap[field] || field;
};

// New model for items in the lesson_outline_plan, mirroring server/models.py
export interface LessonOutlineItem {
  order: number;
  planned_title: string;
  planned_description?: string;
}

export interface Lesson {
  id: string; // Changed from optional, assuming server provides it
  course_id: string; // Added, assuming server provides it
  title: string;
  planned_description?: string; // New field
  content_md: string | null; // Can be null
  external_links: string[];
  generation_status: LessonStatus; // New field for generation process
  status: UserLessonStatus; // User-facing status
  order_in_course?: number; // New field

  // Frontend specific: slug for URL, derived from title or index
  // This might be less relevant if using lesson.id for navigation
  slug?: string; 
  // Frontend specific: index for navigation if no unique ID from backend
  index?: number;
}

export interface Course {
  id: string; // Assuming ID is always present when fetched
  title: string;
  subject: string;
  description: string;
  icon?: string; // For emoji or custom icon identifier
  difficulty?: CourseDifficulty;
  field?: CourseField; // New field for field of study
  lesson_outline_plan?: LessonOutlineItem[]; // New field
  lessons: Lesson[];
  generation_status?: CourseStatus; // New field for course generation status
  status?: UserCourseStatus; // Added from CourseUpdate model possibility
  level?: CourseLevel;   // Added from CourseUpdate model possibility
  created_at?: string; // Added, consider if datetime parsing is needed client-side
  updated_at?: string; // Added
}

export interface CourseCreateRequest {
  title: string;
  subject: string;
  difficulty: CourseDifficulty;
}

export interface CourseCreationResponse {
  id: string;
  message: string;
  icon_suggestion?: string;
}

export interface CourseUpdate {
  title?: string;
  subject?: string;
  description?: string;
  status?: UserCourseStatus;
  level?: CourseLevel;
  icon?: string;
  field?: CourseField; // New field for field of study
  lesson_outline_plan?: LessonOutlineItem[]; // Allow updating the plan
  // lessons?: Lesson[]; // Removed from server's CourseUpdateRequest, reflecting here
} 