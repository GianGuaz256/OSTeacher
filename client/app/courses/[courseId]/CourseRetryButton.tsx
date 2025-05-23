'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';
import { retryCourseGeneration, getCourseById } from '@/lib/api';
import type { Course } from '@/lib/types';
import { CourseStatus, LessonStatus } from '@/lib/types';

interface CourseRetryButtonProps {
  courseId: string;
}

export default function CourseRetryButton({ courseId }: CourseRetryButtonProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryStarted, setRetryStarted] = useState(false);
  const [course, setCourse] = useState<Course | null>(null);
  const router = useRouter();

  // Poll for course updates when retry is in progress
  useEffect(() => {
    if (!retryStarted) return;

    const pollInterval = setInterval(async () => {
      try {
        const updatedCourse = await getCourseById(courseId);
        if (updatedCourse) {
          setCourse(updatedCourse);
          
          // Check if generation is complete or failed
          if (updatedCourse.generation_status === CourseStatus.COMPLETED) {
            console.log('Course generation completed successfully');
            setIsRetrying(false);
            setRetryStarted(false);
            clearInterval(pollInterval);
            // Refresh the page to show final state
            router.refresh();
          } else if (updatedCourse.generation_status === CourseStatus.GENERATION_FAILED) {
            console.log('Course generation failed');
            setIsRetrying(false);
            setRetryStarted(false);
            setError('Course generation failed. Please try again.');
            clearInterval(pollInterval);
          }
        }
      } catch (err) {
        console.error('Error polling for course updates:', err);
      }
    }, 2000); // Poll every 2 seconds

    // Cleanup interval on unmount or when retry stops
    return () => clearInterval(pollInterval);
  }, [retryStarted, courseId, router]);

  const handleRetryCourseGeneration = async () => {
    setIsRetrying(true);
    setError(null);
    try {
      const retriedCourse = await retryCourseGeneration(courseId);
      if (retriedCourse) {
        console.log('Retry course generation started successfully');
        setCourse(retriedCourse);
        setRetryStarted(true);
        // Keep isRetrying true until generation completes
      } else {
        setError('Failed to start course retry. Please try again.');
        setIsRetrying(false);
      }
    } catch (err: any) {
      console.error('Error retrying course generation:', err);
      setError(err.response?.data?.detail || 'An error occurred while retrying course generation.');
      setIsRetrying(false);
    }
  };

  // Helper function to get current generation progress
  const getGenerationProgress = () => {
    if (!course) return null;
    
    const totalLessons = course.lessons.length;
    const completedLessons = course.lessons.filter(lesson => 
      lesson.generation_status === LessonStatus.COMPLETED
    ).length;
    const generatingLessons = course.lessons.filter(lesson => 
      lesson.generation_status === LessonStatus.GENERATING
    ).length;
    const failedLessons = course.lessons.filter(lesson => 
      lesson.generation_status === LessonStatus.GENERATION_FAILED
    ).length;
    
    return {
      total: totalLessons,
      completed: completedLessons,
      generating: generatingLessons,
      failed: failedLessons
    };
  };

  const progress = getGenerationProgress();

  return (
    <div className="mt-4 p-4 border rounded-lg bg-yellow-50 border-yellow-200">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium text-yellow-800">Course Generation Issue Detected</h4>
          <p className="text-sm text-yellow-700 mt-1">
            Some lessons failed to generate or are still pending. You can retry the generation process to complete the missing content.
          </p>
          
          {progress && retryStarted && (
            <div className="mt-2 text-sm text-yellow-700">
              <div className="flex items-center space-x-4">
                <span className="flex items-center">
                  <CheckCircle2 className="h-4 w-4 text-green-600 mr-1" />
                  {progress.completed}/{progress.total} completed
                </span>
                {progress.generating > 0 && (
                  <span className="flex items-center">
                    <RefreshCw className="h-4 w-4 text-blue-600 mr-1 animate-spin" />
                    {progress.generating} generating
                  </span>
                )}
                {progress.failed > 0 && (
                  <span className="flex items-center">
                    <AlertTriangle className="h-4 w-4 text-red-600 mr-1" />
                    {progress.failed} failed
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
        
        <Button 
          onClick={handleRetryCourseGeneration}
          disabled={isRetrying}
          variant="outline"
          className="border-yellow-300 text-yellow-800 hover:bg-yellow-100"
        >
          {isRetrying ? (
            <>
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              {retryStarted ? 'Generating...' : 'Starting...'}
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry Generation
            </>
          )}
        </Button>
      </div>
      
      {error && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}
    </div>
  );
} 