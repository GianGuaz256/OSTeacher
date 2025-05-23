import axios from 'axios';
import type { Course, CourseCreationResponse, CourseCreateRequest, CourseUpdate, Lesson, UserLessonStatus } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper function to generate slugs (simple version)
export function slugify(text: string): string {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-') // Replace spaces with -
    .replace(/[^\w\-]+/g, '') // Remove all non-word chars
    .replace(/\-\-+/g, '-'); // Replace multiple - with single -
}

// Function to process courses and add slugs/indexes to lessons
function processCourseData(course: Course): Course {
  return {
    ...course,
    lessons: course.lessons.map((lesson, index) => ({
      ...lesson,
      slug: lesson.slug || slugify(lesson.title), 
      index: lesson.order_in_course !== undefined ? lesson.order_in_course : index, 
    })),
  };
}

export async function getAllCourses(skip: number = 0, limit: number = 100): Promise<Course[]> {
  try {
    const response = await apiClient.get<Course[]>('/courses/', {
      params: { skip, limit },
    });
    return response.data.map(processCourseData); // Process each course
  } catch (error) {
    console.error("Failed to fetch courses:", error);
    // In a real app, handle this more gracefully, maybe return an error object or throw a custom error
    return []; 
  }
}

export async function getCourseById(courseId: string): Promise<Course | null> {
  try {
    const response = await apiClient.get<Course>(`/courses/${courseId}`);
    return processCourseData(response.data); // Process the course data
  } catch (error) {
    console.error(`Failed to fetch course ${courseId}:`, error);
    return null;
  }
}

// Note: Create and Update functions are not strictly needed for the 3-page UI plan but included for completeness
export async function createCourse(data: CourseCreateRequest): Promise<CourseCreationResponse | null> {
  try {
    const response = await apiClient.post<CourseCreationResponse>('/courses/', data);
    return response.data;
  } catch (error) {
    console.error("Failed to create course:", error);
    return null;
  }
}

export async function updateCourse(courseId: string, data: CourseUpdate): Promise<Course | null> {
  try {
    const response = await apiClient.patch<Course>(`/courses/${courseId}`, data);
    return processCourseData(response.data); // Process the updated course data
  } catch (error) {
    console.error(`Failed to update course ${courseId}:`, error);
    return null;
  }
}

// New function to regenerate a lesson
export async function regenerateLesson(lessonId: string): Promise<Course | null> { // Assuming it returns the updated Course, or adjust as needed
  try {
    // The backend route is POST /lessons/{lesson_id}/regenerate and returns the updated Lesson model
    // However, the client might want the full updated Course object to refresh UI easily.
    // For now, let's assume we just get the lesson back. If the full course is needed,
    // we might need to call getCourseById again or the backend could return the full course.
    // Based on server/routers/lessons.py, it returns the Lesson model.
    const response = await apiClient.post<Lesson>(`/lessons/${lessonId}/regenerate`);
    // If the API returns the updated Lesson, we need a way to update it within the client's state.
    // This function returning the lesson might be more direct.
    // For now, returning null and assuming page will refetch or handle state update.
    // OR, let's make it return the lesson and the page can decide what to do.
    return response.data as any; // Cast to any to avoid type conflicts if it's just Lesson
                                 // A better approach would be to define a proper return type or strategy
  } catch (error) {
    console.error(`Failed to regenerate lesson ${lessonId}:`, error);
    // Consider throwing the error or returning a specific error object for better handling
    return null;
  }
}

export async function updateLessonUserStatus(lessonId: string, status: UserLessonStatus): Promise<Lesson | null> {
  try {
    const response = await apiClient.put<Lesson>(
      `/lessons/${lessonId}/user-status`,
      null, // Sending null as the body, as data is in query params
      {
        params: { status_update: status }, // Send status as a query parameter
        headers: {
          // 'Content-Type': 'application/json', // Content-Type might not be needed if there's no body
        },
      }
    );
    console.log(`[API Client] Received response for lesson ${lessonId} status update:`, response.data);
    return response.data;
  } catch (error: any) { // Added :any to error to access error.response
    console.error(`[API Client] Failed to update user status for lesson ${lessonId} to ${status}. Error:`, error);
    if (error.response) {
      console.error(`[API Client] Error response data:`, error.response.data);
      console.error(`[API Client] Error response status:`, error.response.status);
      console.error(`[API Client] Error response headers:`, error.response.headers);
    }
    return null;
  }
}

// New function to retry course generation
export async function retryCourseGeneration(courseId: string): Promise<Course | null> {
  try {
    const response = await apiClient.post<Course>(`/courses/${courseId}/retry`);
    return response.data;
  } catch (error) {
    console.error(`Failed to retry course generation for course ${courseId}:`, error);
    return null;
  }
} 