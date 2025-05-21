'use client';

import Link from 'next/link';
import { getCourseById, regenerateLesson, updateLessonUserStatus } from '@/lib/api';
import type { Course, Lesson } from '@/lib/types';
import { LessonStatus, UserLessonStatus } from '@/lib/types';
import { notFound, useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { CheckCircle2, Hourglass, RefreshCcw, AlertTriangle, HelpCircle, RefreshCw as RefreshCwIcon, Sparkles, ArrowLeft, ArrowRight, Circle, Play, RotateCcw } from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';
import YouTubeEmbed from '@/components/custom/YouTubeEmbed';
import Lottie from "lottie-react";

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
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCompletionAnimation, setShowCompletionAnimation] = useState(false);

  // Define LottieAnimation component
  const LottieAnimation = ({ animationPath, loop = true, autoplay = true }: { animationPath: string; loop?: boolean; autoplay?: boolean; }) => {
    const [animationData, setAnimationData] = useState<any>(null);

    useEffect(() => {
      fetch(animationPath)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          setAnimationData(data);
        })
        .catch(error => console.error("Error loading Lottie animation:", error));
    }, [animationPath]);

    if (!animationData) {
      return <div>Loading animation...</div>;
    }
    
    return <Lottie 
      animationData={animationData} 
      loop={loop} 
      autoplay={autoplay} 
      style={{
        height: '100%',
        width: '100%',
        position: 'fixed', 
        top: '50%', 
        left: '50%', 
        transform: 'translate(-50%, -50%)',
        zIndex: 9999
      }} 
    />;
  };

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

  const handleUpdateUserStatus = async (newStatus: UserLessonStatus) => {
    if (!lesson || !lesson.id) return;
    setIsUpdatingStatus(true);
    setError(null);
    try {
      const updatedLesson = await updateLessonUserStatus(lesson.id, newStatus);
      if (updatedLesson) {
        setLesson(updatedLesson);
        const fetchedCourse = await getCourseById(params.courseId);
        if (fetchedCourse) {
          setCourse(fetchedCourse);
        }
        if (newStatus === UserLessonStatus.COMPLETED) {
          setShowCompletionAnimation(true);
          setTimeout(() => {
            setShowCompletionAnimation(false);
          }, 3000); // Show animation for 3 seconds
        }
        router.refresh();
      } else {
        setError(`Failed to update lesson status to ${newStatus}.`);
      }
    } catch (e) {
      console.error(`Failed to update lesson status to ${newStatus}:`, e);
      setError(`An error occurred while updating status to ${newStatus}.`);
    } finally {
      setIsUpdatingStatus(false);
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

  const getStatusIcon = (genStatus: LessonStatus, userStatus: UserLessonStatus) => {
    // Prioritize generation status for icons if content isn't ready
    if (genStatus === LessonStatus.GENERATING) {
      return <RefreshCwIcon className="h-7 w-7 text-blue-500 animate-spin" />;
    }
    if (genStatus === LessonStatus.GENERATION_FAILED) {
      return <AlertTriangle className="h-7 w-7 text-red-500" />;
    }
    if (genStatus === LessonStatus.PLANNED) {
      return <Hourglass className="h-7 w-7 text-yellow-500" />;
    }
    if (genStatus === LessonStatus.NEEDS_REVIEW) {
      return <HelpCircle className="h-7 w-7 text-orange-500" />;
    }

    // If generation is complete, use user-facing status for icon
    switch (userStatus) {
      case UserLessonStatus.COMPLETED:
        return <CheckCircle2 className="h-7 w-7 text-green-500" />;
      case UserLessonStatus.IN_PROGRESS:
        return <Hourglass className="h-7 w-7 text-indigo-500" />; // Consider a different icon or color for clarity
      case UserLessonStatus.NOT_STARTED:
        return <Circle className="h-7 w-7 text-gray-400" />;
      default:
        return <Circle className="h-7 w-7 text-gray-300" />; // Fallback for unknown user status
    }
  };

  const getYouTubeVideoId = (url: string): string | null => {
    try {
      const urlObj = new URL(url);
      if (urlObj.hostname === 'www.youtube.com' || urlObj.hostname === 'youtube.com') {
        if (urlObj.pathname === '/watch') {
          return urlObj.searchParams.get('v');
        }
        if (urlObj.pathname.startsWith('/embed/')) {
          return urlObj.pathname.split('/embed/')[1].split('?')[0];
        }
      } else if (urlObj.hostname === 'youtu.be') {
        return urlObj.pathname.substring(1).split('?')[0];
      }
    } catch (e) {
      console.warn("Error parsing YouTube URL:", url, e);
    }
    return null;
  };

  const youtubeLinks = lesson.external_links?.filter(link => getYouTubeVideoId(link)) || [];
  const otherLinks = lesson.external_links?.filter(link => !getYouTubeVideoId(link)) || [];

  const currentLessonIndex = course.lessons.findIndex(l => l.id === lesson.id);
  
  let previousLesson: Lesson | null = null;
  if (currentLessonIndex > 0) {
    previousLesson = course.lessons[currentLessonIndex - 1];
  }

  let nextLesson: Lesson | null = null;
  if (currentLessonIndex !== -1 && currentLessonIndex < course.lessons.length - 1) {
    nextLesson = course.lessons[currentLessonIndex + 1];
  }

  return (
    <div className="container mx-auto p-4">
      <div className="mb-4 flex justify-start">
        <Button variant="outline" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
        </Button>
      </div>
      <header className="mb-8 text-center">
        <p className="text-sm text-muted-foreground">
          <Link href={`/courses/${course.id}`} className="hover:underline">{course.title}</Link>
        </p>
        <div className="flex items-center justify-center mt-1">
          <h1 className="text-4xl font-bold tracking-tight">{lesson.title}</h1>
          <span className="ml-3">{getStatusIcon(lesson.generation_status, lesson.status)}</span>
        </div>
        {lesson.planned_description && (
          <p className="text-lg text-muted-foreground mt-2 px-4">
            {lesson.planned_description}
          </p>
        )}
      </header>

      <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4 mb-6">
        <Button onClick={handleRegenerateLesson} disabled={isRegenerating} variant="outline">
          {isRegenerating && <Sparkles className="mr-2 h-4 w-4 animate-spin" />}
          Regenerate Lesson
        </Button>
      </div>

      {showCompletionAnimation && (
        <LottieAnimation animationPath="/animation.json" loop={false} />
      )}

      <div className="flex flex-col sm:flex-row items-center justify-center space-y-2 sm:space-y-0 sm:space-x-4 mb-6">
        {lesson.status !== UserLessonStatus.IN_PROGRESS && (
          <Button 
            onClick={() => handleUpdateUserStatus(UserLessonStatus.IN_PROGRESS)} 
            disabled={isUpdatingStatus || lesson.generation_status !== LessonStatus.COMPLETED}
            variant="outline"
          >
            <Play className="mr-2 h-4 w-4" /> Mark as In Progress
          </Button>
        )}
        {lesson.status !== UserLessonStatus.COMPLETED && (
          <Button 
            onClick={() => handleUpdateUserStatus(UserLessonStatus.COMPLETED)} 
            disabled={isUpdatingStatus || lesson.generation_status !== LessonStatus.COMPLETED}
            variant="outline"
          >
            <CheckCircle2 className="mr-2 h-4 w-4" /> Mark as Completed
          </Button>
        )}
        {lesson.status !== UserLessonStatus.NOT_STARTED && (
          <Button 
            onClick={() => handleUpdateUserStatus(UserLessonStatus.NOT_STARTED)} 
            disabled={isUpdatingStatus || lesson.generation_status !== LessonStatus.COMPLETED}
            variant="outline"
          >
            <RotateCcw className="mr-2 h-4 w-4" /> Reset to Not Started
          </Button>
        )}
      </div>

      <article className="w-full bg-card p-2 sm:p-4 md:p-6 shadow-md rounded-md border">
        <MarkdownRenderer markdown={finalMarkdown} />
      </article>

      {(youtubeLinks.length > 0 || otherLinks.length > 0) && (
        <section className="mt-8 pt-4 border-t">
          <h3 className="text-xl font-semibold mb-3 text-center">External Resources</h3>
          
          {youtubeLinks.length > 0 && (
            <div className="space-y-4">
              {youtubeLinks.map((link, index) => {
                const videoId = getYouTubeVideoId(link); // Already filtered, so videoId should exist
                if (videoId) { // Still good practice to check
                  return (
                    <div key={`youtube-${index}`} className="max-w-2xl mx-auto">
                      <YouTubeEmbed videoId={videoId} />
                      <p className="text-sm text-center mt-1">
                        <a href={link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                          Watch on YouTube: {link}
                        </a>
                      </p>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          )}
          
          {otherLinks.length > 0 && (
            <div className="mt-6">
              <h4 className="text-lg font-medium mb-2 text-center">Other Links</h4>
              <ul className="list-disc list-inside space-y-1 text-center">
                {otherLinks.map((link, index) => (
                  <li key={`other-${index}`}>
                    <a href={link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <div className="mt-12 text-center space-x-4">
        {previousLesson && (
          <Link href={`/courses/${course.id}/lessons/${previousLesson.id}`} passHref>
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" /> Previous Lesson
            </Button>
          </Link>
        )}
        <Link href={`/courses/${course.id}`} passHref>
          <Button variant="outline">
            Back to Course Lessons
          </Button>
        </Link>
        {nextLesson && (
          <Link href={`/courses/${course.id}/lessons/${nextLesson.id}`} passHref>
            <Button variant="default">
              Next Lesson <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
} 