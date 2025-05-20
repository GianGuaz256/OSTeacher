export enum LessonStatus {
  PLANNED = "planned",
  GENERATING = "generating",
  COMPLETED = "completed",
  GENERATION_FAILED = "generation_failed",
  NEEDS_REVIEW = "needs_review",
  PENDING = "pending", // Retained for now, consider phasing out if not used
}

export enum CourseStatus {
  DRAFT = "draft",
  PUBLISHED = "published",
  ARCHIVED = "archived",
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
  status: LessonStatus;
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
  lesson_outline_plan?: LessonOutlineItem[]; // New field
  lessons: Lesson[];
  status?: CourseStatus; // Added from CourseUpdate model possibility
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
  status?: CourseStatus;
  level?: CourseLevel;
  icon?: string;
  lesson_outline_plan?: LessonOutlineItem[]; // Allow updating the plan
  // lessons?: Lesson[]; // Removed from server's CourseUpdateRequest, reflecting here
} 