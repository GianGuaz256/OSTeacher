'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, AlertTriangle, Loader2 } from 'lucide-react';
import { getQuizByLessonId, updateQuizPassedStatus, markQuizAsAttempted, getCourseById } from '@/lib/api';
import QuizComponent from '@/components/quiz/QuizComponent';
import type { Quiz, Course, Lesson } from '@/lib/types';

interface QuizPageProps {
  params: {
    courseId: string;
    lessonSlug: string;
  };
}

export default function QuizPage({ params }: QuizPageProps) {
  const router = useRouter();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch course and lesson data
        const courseData = await getCourseById(params.courseId);
        if (!courseData) {
          setError('Course not found');
          return;
        }
        
        setCourse(courseData);
        
        // Find the lesson
        const lessonData = courseData.lessons.find(l => l.id === params.lessonSlug);
        if (!lessonData) {
          setError('Lesson not found');
          return;
        }
        
        setLesson(lessonData);
        
        // Fetch quiz data
        const quizData = await getQuizByLessonId(params.lessonSlug);
        if (!quizData) {
          setError('No quiz found for this lesson');
          return;
        }
        
        setQuiz(quizData);
      } catch (err) {
        console.error('Error fetching quiz data:', err);
        setError('Failed to load quiz data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [params.courseId, params.lessonSlug]);

  const handleQuizComplete = async (score: number, passed: boolean, timeTaken: number) => {
    if (!quiz) {
      return;
    }
    
    setIsUpdatingStatus(true);
    try {
      const updatedQuiz = await updateQuizPassedStatus(quiz.id, passed);
      if (updatedQuiz) {
        setQuiz(updatedQuiz);
      }
    } catch (err) {
      console.error('Error updating quiz status:', err);
      // Don't show error to user as the quiz was completed successfully
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleQuizStart = async () => {
    if (!quiz) return;
    
    // Mark quiz as attempted in the database
    try {
      const updatedQuiz = await markQuizAsAttempted(quiz.id);
      if (updatedQuiz) {
        setQuiz(updatedQuiz);
      }
    } catch (err) {
      console.error('Error marking quiz as started:', err);
      // Don't prevent quiz from starting if API call fails
    }
  };

  const handleRetry = () => {
    // Reset quiz state by refetching
    window.location.reload();
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="flex items-center space-x-2">
            <Loader2 className="h-6 w-6 animate-spin" />
            <span>Loading quiz...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-4">
        <div className="mb-4">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Go Back
          </Button>
        </div>
        
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center space-y-4">
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
            <h2 className="text-xl font-semibold">Quiz Not Available</h2>
            <p className="text-muted-foreground max-w-md">{error}</p>
            <div className="space-x-2">
              <Button variant="outline" onClick={() => router.back()}>
                Go Back to Lesson
              </Button>
              <Button onClick={() => window.location.reload()}>
                Try Again
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!quiz || !course || !lesson) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold">Quiz Not Found</h2>
            <p className="text-muted-foreground">This lesson doesn't have a quiz available.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <Button variant="outline" onClick={() => router.back()}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Lesson
          </Button>
          
          <div className="text-right">
            <p className="text-sm text-muted-foreground">
              <Link href={`/courses/${course.id}`} className="hover:underline">
                {course.title}
              </Link>
              {' > '}
              <Link href={`/courses/${course.id}/lessons/${lesson.id}`} className="hover:underline">
                {lesson.title}
              </Link>
            </p>
          </div>
        </div>
        
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight mb-2">
            {lesson.title} - Quiz
          </h1>
          {lesson.planned_description && (
            <p className="text-muted-foreground">
              Test your understanding of: {lesson.planned_description}
            </p>
          )}
        </div>
      </div>

      {/* Quiz Component */}
      <div className="flex justify-center">
        <QuizComponent
          quiz={quiz}
          onQuizComplete={handleQuizComplete}
          onQuizStart={handleQuizStart}
          onRetry={handleRetry}
          className="w-full"
        />
      </div>

      {/* Status indicator */}
      {isUpdatingStatus && (
        <div className="fixed bottom-4 right-4 bg-blue-100 border border-blue-200 rounded-lg p-3 flex items-center space-x-2">
          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
          <span className="text-sm text-blue-800">Saving quiz results...</span>
        </div>
      )}

      {/* Navigation */}
      <div className="mt-8 text-center">
        <Link href={`/courses/${course.id}/lessons/${lesson.id}`}>
          <Button variant="outline">
            Return to Lesson
          </Button>
        </Link>
      </div>
    </div>
  );
} 