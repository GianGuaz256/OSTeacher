'use client';

import Link from 'next/link';
import { getCourseById, regenerateLesson } from '@/lib/api';
import type { Course, Lesson } from '@/lib/types';
import { LessonStatus } from '@/lib/types';
import { notFound, useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { CheckCircle2, Hourglass, RefreshCcw, AlertTriangle, HelpCircle, RefreshCw as RefreshCwIcon, Sparkles } from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';

interface LessonDetailPageProps {
  params: {
    courseId: string;
    lessonSlug: string;
  };
}

export default function LessonDetailPage({ params }: LessonDetailPageProps) {
  const router = useRouter();
  const [course, setCourse] = useState<Course | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLessonData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedCourse = await getCourseById(params.courseId);
      if (fetchedCourse) {
        setCourse(fetchedCourse);
        const currentLesson = fetchedCourse.lessons.find(l => l.id === params.lessonSlug);
        if (currentLesson) {
          setLesson(currentLesson);
        } else {
          console.error(`Lesson with ID ${params.lessonSlug} not found in course ${params.courseId}`);
          notFound();
        }
      } else {
        notFound();
      }
    } catch (e) {
      console.error("Failed to fetch lesson data:", e);
      setError("Failed to load lesson data.");
    } finally {
      setIsLoading(false);
    }
  }, [params.courseId, params.lessonSlug]);

  useEffect(() => {
    fetchLessonData();
  }, [fetchLessonData]);

  const handleRegenerateLesson = async () => {
    if (!lesson || !lesson.id) return;

    setIsRegenerating(true);
    setError(null);
    try {
      const regeneratedLesson = await regenerateLesson(lesson.id);
      if (regeneratedLesson) {
        await fetchLessonData();
        router.refresh();
      } else {
        setError("Failed to regenerate lesson. The lesson might not have been found or an error occurred.");
      }
    } catch (e) {
      console.error("Failed to regenerate lesson:", e);
      setError("An error occurred while regenerating the lesson.");
    } finally {
      setIsRegenerating(false);
    }
  };

  if (isLoading) {
    return <div className="container mx-auto p-4 text-center">Loading lesson...</div>;
  }

  if (error) {
    return <div className="container mx-auto p-4 text-center text-red-500">Error: {error} <Button onClick={fetchLessonData} variant="outline" className="ml-2">Try Again</Button></div>;
  }

  if (!course || !lesson) {
    return <div className="container mx-auto p-4 text-center">Lesson not found.</div>;
  }

  const stripOuterMarkdownCodeBlock = (md: string | null | undefined): string => {
    if (!md || md.trim() === '') return '';
    let processedMd = md.trim();
    const prefix = "```markdown";
    const suffix = "```";
    if (processedMd.startsWith(prefix) && processedMd.endsWith(suffix)) {
      const coreContent = processedMd.substring(prefix.length, processedMd.length - suffix.length);
      return coreContent.trim();
    }
    return processedMd;
  };
  
  let finalMarkdown: string;

  if (lesson.content_md === null) {
    finalMarkdown = "_Content is being generated or is not available._";
  } else {
    const strippedContent = stripOuterMarkdownCodeBlock(lesson.content_md);
    if (strippedContent.trim() === "") {
      // If content_md was present but resulted in an empty string after processing (e.g., it was just "```markdown```" or whitespace)
      finalMarkdown = "_Content is currently empty._";
    } else {
      finalMarkdown = strippedContent;
    }
  }

  const getStatusIcon = (status: LessonStatus) => {
    switch (status) {
      case LessonStatus.COMPLETED:
        return <CheckCircle2 className="h-7 w-7 text-green-500" />;
      case LessonStatus.GENERATING:
        return <RefreshCwIcon className="h-7 w-7 text-blue-500 animate-spin" />;
      case LessonStatus.PLANNED:
        return <Hourglass className="h-7 w-7 text-yellow-500" />;
      case LessonStatus.GENERATION_FAILED:
        return <AlertTriangle className="h-7 w-7 text-red-500" />;
      case LessonStatus.NEEDS_REVIEW:
        return <HelpCircle className="h-7 w-7 text-orange-500" />;
      default:
        return <Hourglass className="h-7 w-7 text-gray-400" />;
    }
  };

  return (
    <div className="container mx-auto p-4">
      <header className="mb-8 text-center">
        <p className="text-sm text-muted-foreground">
          <Link href={`/courses/${course.id}`} className="hover:underline">{course.title}</Link>
        </p>
        <div className="flex items-center justify-center mt-1">
          <h1 className="text-4xl font-bold tracking-tight">{lesson.title}</h1>
          <span className="ml-3">{getStatusIcon(lesson.status)}</span>
        </div>
        {lesson.planned_description && (
          <p className="text-lg text-muted-foreground mt-2">{lesson.planned_description}</p>
        )}
      </header>

      <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4 mb-6">
        <Button onClick={handleRegenerateLesson} disabled={isRegenerating} variant="outline">
          {isRegenerating && <Sparkles className="mr-2 h-4 w-4 animate-spin" />}
          Regenerate Lesson
        </Button>
      </div>

      <article className="w-full bg-card p-2 sm:p-4 md:p-6 shadow-md rounded-md border">
        <MarkdownRenderer markdown={finalMarkdown} />
      </article>

      {lesson.external_links && lesson.external_links.length > 0 && (
        <section className="mt-8 pt-4 border-t">
          <h3 className="text-xl font-semibold mb-3 text-center">External Links</h3>
          <ul className="list-disc list-inside space-y-1 text-center">
            {lesson.external_links.map((link, index) => (
              <li key={index}>
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {link}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-12 text-center space-x-4">
        <Link href={`/courses/${course.id}`} passHref>
          <Button variant="outline">
            Back to Course Lessons
          </Button>
        </Link>
      </div>
    </div>
  );
} 