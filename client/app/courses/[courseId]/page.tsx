import Link from 'next/link';
import { getCourseById } from '@/lib/api';
import type { Course, Lesson, LessonOutlineItem } from '@/lib/types';
import { LessonStatus, UserLessonStatus, UserCourseStatus, CourseStatus } from '@/lib/types';
import { notFound } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Hourglass, AlertTriangle, RefreshCw, HelpCircle, ArrowLeft, Circle } from 'lucide-react';
import CourseRetryButton from './CourseRetryButton';

export const dynamic = 'force-dynamic';

interface CourseDetailPageProps {
  params: {
    courseId: string;
  };
}

export async function generateMetadata({ params }: CourseDetailPageProps) {
  const course = await getCourseById(params.courseId);
  if (!course) {
    return { title: 'Course Not Found' };
  }
  return { title: course.title };
}

async function CourseDetailPage({ params }: CourseDetailPageProps) {
  const course = await getCourseById(params.courseId);

  if (!course) {
    notFound();
  }

  // Helper function to check if retry button should be shown
  const shouldShowRetryButton = () => {
    // Show retry button if:
    // 1. Course is not currently being generated as a whole
    // 2. There are lessons that need generation (planned, failed, or stuck generating)
    // 3. Course generation has failed OR course is completed OR course is in draft with problematic lessons
    // 4. Course is completed but has fewer lessons than planned
    
    const isGenerationFailed = course.generation_status === CourseStatus.GENERATION_FAILED;
    const isGenerationCompleted = course.generation_status === CourseStatus.COMPLETED;
    const isGenerationDraft = course.generation_status === CourseStatus.DRAFT;
    const isCurrentlyGenerating = course.generation_status === CourseStatus.GENERATING;
    
    // Don't show button if course is currently being generated
    if (isCurrentlyGenerating) return false;
    
    // Check if there are lessons that need generation or are stuck
    const hasFailedOrPlannedLessons = course.lessons.some(lesson => 
      lesson.generation_status === LessonStatus.GENERATION_FAILED || 
      lesson.generation_status === LessonStatus.PLANNED
    );
    
    // Check for lessons stuck in generating status
    const hasStuckGeneratingLessons = course.lessons.some(lesson => 
      lesson.generation_status === LessonStatus.GENERATING
    );
    
    // Check if course was created more than 5 minutes ago (indicating potential timeout)
    const courseAge = course.created_at ? Date.now() - new Date(course.created_at).getTime() : 0;
    const isOldEnoughForTimeout = courseAge > 5 * 60 * 1000; // 5 minutes in milliseconds
    
    // Check if course is completed but has fewer lessons than planned
    const plannedLessonCount = course.lesson_outline_plan ? course.lesson_outline_plan.length : 0;
    const actualLessonCount = course.lessons.length;
    const completedLessonCount = course.lessons.filter(lesson => 
      lesson.generation_status === LessonStatus.COMPLETED
    ).length;
    const hasFewerLessonsThanPlanned = isGenerationCompleted && plannedLessonCount > 0 && 
      (actualLessonCount < plannedLessonCount || completedLessonCount < plannedLessonCount);
    
    // Debug logging
    console.log('Course retry button debug:', {
      courseGenerationStatus: course.generation_status,
      isGenerationFailed,
      isGenerationCompleted,
      isGenerationDraft,
      isCurrentlyGenerating,
      hasFailedOrPlannedLessons,
      hasStuckGeneratingLessons,
      courseAge: Math.round(courseAge / 1000 / 60 * 10) / 10, // minutes with 1 decimal
      isOldEnoughForTimeout,
      courseCreatedAt: course.created_at,
      plannedLessonCount,
      actualLessonCount,
      completedLessonCount,
      hasFewerLessonsThanPlanned,
      lessonStatuses: course.lessons.map(l => ({
        title: l.title,
        generation_status: l.generation_status,
        status: l.status
      }))
    });
    
    // Show button if there are lessons that need attention AND one of these conditions:
    // - Course generation failed, OR
    // - Course generation completed but has incomplete lessons, OR  
    // - Course is in draft and has lessons that are stuck generating for 5+ minutes, OR
    // - Course is in draft and has failed/planned lessons, OR
    // - Course is completed but has fewer lessons than planned
    const hasProblematicLessons = hasFailedOrPlannedLessons || (hasStuckGeneratingLessons && isOldEnoughForTimeout);
    const shouldShow = (hasProblematicLessons && (isGenerationFailed || isGenerationCompleted || isGenerationDraft)) || 
                       hasFewerLessonsThanPlanned;
    
    console.log('Should show retry button:', shouldShow);
    
    return shouldShow;
  };

  return (
    <div className="container mx-auto p-4">
      <div className="mb-4 flex justify-start">
        <Link href="/dashboard" passHref>
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
          </Button>
        </Link>
      </div>
      
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight">{course.title}</h1>
        {course.icon && <p className="text-5xl my-4">{course.icon}</p>}
        <p className="text-xl text-muted-foreground mt-2">{course.subject}</p>
        {course.created_at && <p className="text-sm text-muted-foreground">Created: {new Date(course.created_at).toLocaleDateString()}</p>}
        {course.updated_at && <p className="text-sm text-muted-foreground">Last Updated: {new Date(course.updated_at).toLocaleDateString()}</p>}
      </header>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Course Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p> <span className="font-semibold">Description:</span> {course.description}</p>
          {course.difficulty && (
            <p>
              <span className="font-semibold">Difficulty:</span> 
              <span 
                className={`ml-2 px-2 py-0.5 rounded-md border font-medium ${ 
                  course.difficulty.toLowerCase() === 'easy' ? 'border-green-500 text-green-700 bg-green-50' :
                  course.difficulty.toLowerCase() === 'medium' ? 'border-yellow-500 text-yellow-700 bg-yellow-50' :
                  course.difficulty.toLowerCase() === 'hard' ? 'border-red-500 text-red-700 bg-red-50' : 'border-gray-300'
                }`}
              >
                {course.difficulty.toUpperCase()}
              </span>
            </p>
          )}
          {course.level && (
            <p><span className="font-semibold">Level:</span> {course.level.toUpperCase()}</p>
          )}
          {course.status && (
            <p>
              <span className="font-semibold">Status:</span> 
              <span 
                className={`ml-2 px-2 py-0.5 rounded-md border text-xs font-medium ${
                  course.status.toLowerCase() === UserCourseStatus.NOT_STARTED.toLowerCase() ? 'border-gray-400 text-gray-600 bg-gray-100' :
                  course.status.toLowerCase() === UserCourseStatus.IN_PROGRESS.toLowerCase() ? 'border-yellow-500 text-yellow-700 bg-yellow-100' :
                  course.status.toLowerCase() === UserCourseStatus.COMPLETED.toLowerCase() ? 'border-green-500 text-green-700 bg-green-100' : 'border-gray-300 text-gray-500 bg-gray-50'
                }`}
              >
                {course.status.replace('_', ' ').toUpperCase()}
              </span>
            </p>
          )}
          {course.generation_status && (course.generation_status === CourseStatus.DRAFT || course.generation_status === CourseStatus.GENERATING || course.generation_status === CourseStatus.GENERATION_FAILED) && (
            <p>
              <span className="font-semibold">Generation Status:</span> 
              <span 
                className={`ml-2 px-2 py-0.5 rounded-md border text-xs font-medium ${
                  course.generation_status.toLowerCase() === CourseStatus.DRAFT.toLowerCase() ? 'border-purple-500 text-purple-700 bg-purple-100' :
                  course.generation_status.toLowerCase() === CourseStatus.GENERATING.toLowerCase() ? 'border-blue-500 text-blue-700 bg-blue-100' :
                  course.generation_status.toLowerCase() === CourseStatus.GENERATION_FAILED.toLowerCase() ? 'border-red-500 text-red-700 bg-red-100' : 'border-gray-300 text-gray-500 bg-gray-50'
                }`}
              >
                {course.generation_status.replace('_', ' ').toUpperCase()}
              </span>
            </p>
          )}
          
          {/* Retry Button - Client Component */}
          {shouldShowRetryButton() && (
            <CourseRetryButton courseId={course.id} />
          )}
          
          {course.lesson_outline_plan && course.lesson_outline_plan.length > 0 && (
            <details className="pt-2 group">
              <summary className="font-semibold cursor-pointer hover:text-primary list-none">
                <span className="group-open:hidden">▶ Show Lesson Outline Plan</span>
                <span className="hidden group-open:inline">▼ Hide Lesson Outline Plan</span>
              </summary>
              <ol className="list-none list-inside pl-4 text-sm text-muted-foreground mt-2">
                {course.lesson_outline_plan.map((item: LessonOutlineItem) => (
                  <li key={item.order}>{item.order}. {item.planned_title}{item.planned_description ? `: ${item.planned_description}` : ''}</li>
                ))}
              </ol>
            </details>
          )}
        </CardContent>
      </Card>

      <section>
        <h2 className="text-3xl font-semibold mb-6 text-center">Lessons</h2>
        {course.lessons && course.lessons.length > 0 ? (
          <ul className="space-y-3">
            {course.lessons.map((lesson: Lesson) => (
              <li key={lesson.id} className="border p-4 rounded-md hover:bg-muted/50 transition-colors">
                {course.generation_status === CourseStatus.GENERATING ? (
                  <div className="block cursor-not-allowed opacity-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-grow">
                        <h3 className="text-xl font-medium text-primary">
                          {lesson.title}
                        </h3>
                        {lesson.planned_description && <p className="text-sm text-muted-foreground mt-1 px-2 md:px-4">{lesson.planned_description}</p>}
                      </div>
                      <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                        <span className="text-sm text-muted-foreground capitalize">
                          {lesson.status.replace('_', ' ')}
                          {(lesson.generation_status !== LessonStatus.COMPLETED && lesson.generation_status !== LessonStatus.PLANNED && lesson.generation_status.toLowerCase() !== lesson.status.toLowerCase()) && 
                            ` (${lesson.generation_status.replace('_', ' ')})`}
                        </span>
                        {lesson.generation_status === LessonStatus.GENERATING ? (
                          <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
                        ) : lesson.generation_status === LessonStatus.GENERATION_FAILED ? (
                          <AlertTriangle className="h-5 w-5 text-red-500" />
                        ) : lesson.generation_status === LessonStatus.PLANNED ? (
                          <Hourglass className="h-5 w-5 text-yellow-500" />
                        ) : lesson.generation_status === LessonStatus.NEEDS_REVIEW ? (
                          <HelpCircle className="h-5 w-5 text-orange-500" />
                        ) : lesson.status === UserLessonStatus.COMPLETED ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : lesson.status === UserLessonStatus.IN_PROGRESS ? (
                          <Hourglass className="h-5 w-5 text-indigo-500" />
                        ) : lesson.status === UserLessonStatus.NOT_STARTED ? (
                          <Circle className="h-5 w-5 text-gray-400" />
                        ) : (
                          <Circle className="h-5 w-5 text-gray-300" />
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <Link href={`/courses/${course.id}/lessons/${lesson.id}`} className="block">
                    <div className="flex items-center justify-between">
                      <div className="flex-grow">
                        <h3 className="text-xl font-medium text-primary">
                          {lesson.title}
                        </h3>
                        {lesson.planned_description && <p className="text-sm text-muted-foreground mt-1 px-2 md:px-4">{lesson.planned_description}</p>}
                      </div>
                      <div className="flex items-center space-x-2 flex-shrink-0 ml-4">
                        <span className="text-sm text-muted-foreground capitalize">
                          {lesson.status.replace('_', ' ')}
                          {(lesson.generation_status !== LessonStatus.COMPLETED && lesson.generation_status !== LessonStatus.PLANNED && lesson.generation_status.toLowerCase() !== lesson.status.toLowerCase()) && 
                            ` (${lesson.generation_status.replace('_', ' ')})`}
                        </span>
                        {lesson.generation_status === LessonStatus.GENERATING ? (
                          <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
                        ) : lesson.generation_status === LessonStatus.GENERATION_FAILED ? (
                          <AlertTriangle className="h-5 w-5 text-red-500" />
                        ) : lesson.generation_status === LessonStatus.PLANNED ? (
                          <Hourglass className="h-5 w-5 text-yellow-500" />
                        ) : lesson.generation_status === LessonStatus.NEEDS_REVIEW ? (
                          <HelpCircle className="h-5 w-5 text-orange-500" />
                        ) : lesson.status === UserLessonStatus.COMPLETED ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : lesson.status === UserLessonStatus.IN_PROGRESS ? (
                          <Hourglass className="h-5 w-5 text-indigo-500" />
                        ) : lesson.status === UserLessonStatus.NOT_STARTED ? (
                          <Circle className="h-5 w-5 text-gray-400" />
                        ) : (
                          <Circle className="h-5 w-5 text-gray-300" />
                        )}
                      </div>
                    </div>
                  </Link>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-center text-muted-foreground">No lessons available for this course yet.</p>
        )}
      </section>
    </div>
  );
}

export default CourseDetailPage; 