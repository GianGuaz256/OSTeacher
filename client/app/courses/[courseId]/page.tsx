import Link from 'next/link';
import { getCourseById } from '@/lib/api';
import type { Course, Lesson, LessonOutlineItem } from '@/lib/types';
import { LessonStatus } from '@/lib/types';
import { notFound } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Hourglass, AlertTriangle, RefreshCw, HelpCircle } from 'lucide-react';

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

  return (
    <div className="container mx-auto p-4">
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
          <p><span className="font-semibold">Description:</span> {course.description}</p>
          {course.difficulty && (
            <p>
              <span className="font-semibold">Difficulty:</span> 
              <span 
                className={`px-2 py-0.5 rounded-md border font-medium ${ 
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
                className={`px-2 py-0.5 rounded-md border font-medium ${ 
                  course.status.toLowerCase() === 'draft' ? 'border-gray-500 text-gray-700 bg-gray-50' :
                  course.status.toLowerCase() === 'published' ? 'border-green-500 text-green-700 bg-green-50' :
                  course.status.toLowerCase() === 'archived' ? 'border-blue-500 text-blue-700 bg-blue-50' : 'border-gray-300'
                }`}
              >
                {course.status.toUpperCase()}
              </span>
            </p>
          )}
          {course.lesson_outline_plan && course.lesson_outline_plan.length > 0 && (
            <details className="pt-2 group">
              <summary className="font-semibold cursor-pointer hover:text-primary list-none">
                <span className="group-open:hidden">▶ Show Lesson Outline Plan</span>
                <span className="hidden group-open:inline">▼ Hide Lesson Outline Plan</span>
              </summary>
              <ul className="list-disc list-inside pl-4 text-sm text-muted-foreground mt-2">
                {course.lesson_outline_plan.map((item: LessonOutlineItem) => (
                  <li key={item.order}>{item.order}. {item.planned_title}{item.planned_description ? `: ${item.planned_description}` : ''}</li>
                ))}
              </ul>
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
                <Link href={`/courses/${course.id}/lessons/${lesson.id}`} className="block">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-medium text-primary">{lesson.title}</h3>
                      {lesson.planned_description && <p className="text-sm text-muted-foreground mt-1">{lesson.planned_description}</p>}
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-muted-foregroundcapitalize">{lesson.status.replace('_', ' ')}</span>
                      {lesson.status === LessonStatus.COMPLETED ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : lesson.status === LessonStatus.GENERATING ? (
                        <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />
                      ) : lesson.status === LessonStatus.PLANNED ? (
                        <Hourglass className="h-5 w-5 text-yellow-500" />
                      ) : lesson.status === LessonStatus.GENERATION_FAILED ? (
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                      ) : lesson.status === LessonStatus.NEEDS_REVIEW ? (
                        <HelpCircle className="h-5 w-5 text-orange-500" />
                      ) : (
                        <Hourglass className="h-5 w-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-center text-muted-foreground">No lessons available for this course yet.</p>
        )}
      </section>

      <div className="mt-12 text-center">
        <Link href="/dashboard" passHref>
          <Button variant="outline">
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}

export default CourseDetailPage; 