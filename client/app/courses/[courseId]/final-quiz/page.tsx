'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ArrowLeft, AlertTriangle, Loader2, Trophy } from 'lucide-react';
import { getFinalQuizByCourseId, updateQuizPassedStatus, markQuizAsAttempted, getCourseById } from '@/lib/api';
import QuizComponent from '@/components/quiz/QuizComponent';
import type { Quiz, Course } from '@/lib/types';

interface FinalQuizPageProps {
  params: {
    courseId: string;
  };
}

export default function FinalQuizPage({ params }: FinalQuizPageProps) {
  const router = useRouter();
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [course, setCourse] = useState<Course | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch course data
        const courseData = await getCourseById(params.courseId);
        if (!courseData) {
          setError('Course not found');
          return;
        }
        
        setCourse(courseData);
        
        // Fetch final quiz data
        const quizData = await getFinalQuizByCourseId(params.courseId);
        if (!quizData) {
          setError('No final quiz found for this course');
          return;
        }
        
        setQuiz(quizData);
      } catch (err) {
        console.error('Error fetching final quiz data:', err);
        setError('Failed to load final quiz data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [params.courseId]);

  const handleQuizComplete = async (score: number, passed: boolean, timeTaken: number) => {
    if (!quiz) return;
    
    setIsUpdatingStatus(true);
    try {
      const updatedQuiz = await updateQuizPassedStatus(quiz.id, passed);
      if (updatedQuiz) {
        setQuiz(updatedQuiz);
        console.log(`Final quiz completed: Score ${score}%, ${passed ? 'Passed' : 'Failed'}, Time: ${timeTaken}s`);
      }
    } catch (err) {
      console.error('Error updating final quiz status:', err);
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
        console.log('Final quiz started - marked as attempted in database');
      }
    } catch (err) {
      console.error('Error marking final quiz as started:', err);
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
            <span>Loading final quiz...</span>
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
            <h2 className="text-xl font-semibold">Final Quiz Not Available</h2>
            <p className="text-muted-foreground max-w-md">{error}</p>
            <div className="space-x-2">
              <Button variant="outline" onClick={() => router.back()}>
                Go Back to Course
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

  if (!quiz || !course) {
    return (
      <div className="container mx-auto p-4">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <AlertTriangle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold">Final Quiz Not Found</h2>
            <p className="text-muted-foreground">This course doesn't have a final quiz available.</p>
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
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Course
          </Button>
          
          <div className="text-right">
            <p className="text-sm text-muted-foreground">
              <Link href={`/courses/${course.id}`} className="hover:underline">
                {course.title}
              </Link>
            </p>
          </div>
        </div>
        
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Trophy className="h-8 w-8 text-yellow-500 mr-3" />
            <h1 className="text-3xl font-bold tracking-tight">
              Final Quiz
            </h1>
          </div>
          <h2 className="text-xl text-muted-foreground mb-2">
            {course.title}
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            This comprehensive quiz tests your understanding of all the concepts covered throughout the course. 
            You'll need to demonstrate mastery of the material to pass.
          </p>
        </div>
      </div>

      {/* Course Progress Info */}
      {course.lessons && course.lessons.length > 0 && (
        <div className="mb-6 text-center">
          <div className="inline-flex items-center space-x-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <span className="text-sm text-blue-800">
              Course Progress: {course.lessons.length} lessons completed
            </span>
          </div>
        </div>
      )}

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
        <Link href={`/courses/${course.id}`}>
          <Button variant="outline">
            Return to Course
          </Button>
        </Link>
      </div>
    </div>
  );
} 