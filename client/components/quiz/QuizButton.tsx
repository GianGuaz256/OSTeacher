'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { 
  Brain, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Trophy,
  Play,
  RotateCcw
} from 'lucide-react';
import type { Quiz } from '@/lib/types';

interface QuizButtonProps {
  courseId: string;
  lessonId: string;
  quiz: Quiz | null;
  isLoading?: boolean;
  className?: string;
}

export default function QuizButton({ 
  courseId, 
  lessonId, 
  quiz, 
  isLoading = false,
  className = '' 
}: QuizButtonProps) {
  if (isLoading) {
    return (
      <Card className={`w-full ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-center space-x-2">
            <Clock className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading quiz...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!quiz) {
    return (
      <Card className={`w-full border-dashed ${className}`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-center space-x-2 text-muted-foreground">
            <Brain className="h-4 w-4" />
            <span className="text-sm">No quiz available for this lesson</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getQuizStatus = () => {
    if (quiz.passed === null) {
      return {
        status: 'not_attempted',
        label: 'Not Attempted',
        color: 'bg-gray-100 text-gray-700',
        icon: <Play className="h-4 w-4" />
      };
    } else if (quiz.passed === true) {
      return {
        status: 'passed',
        label: 'Passed',
        color: 'bg-green-100 text-green-700',
        icon: <CheckCircle2 className="h-4 w-4" />
      };
    } else {
      return {
        status: 'failed',
        label: 'Failed',
        color: 'bg-red-100 text-red-700',
        icon: <XCircle className="h-4 w-4" />
      };
    }
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    return `${minutes} min`;
  };

  const quizStatus = getQuizStatus();
  const quizUrl = `/courses/${courseId}/lessons/${lessonId}/quiz`;

  return (
    <Card className={`w-full border-l-4 border-l-blue-500 ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <Brain className="h-5 w-5 text-blue-600" />
              </div>
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="text-sm font-semibold text-gray-900 truncate">
                  {quiz.quiz_data.quizTitle}
                </h3>
                <Badge className={`text-xs ${quizStatus.color}`}>
                  {quizStatus.icon}
                  <span className="ml-1">{quizStatus.label}</span>
                </Badge>
              </div>
              
              <p className="text-xs text-gray-500 mb-2 line-clamp-2">
                {quiz.quiz_data.quizSynopsis}
              </p>
              
              <div className="flex items-center space-x-4 text-xs text-gray-500">
                <div className="flex items-center space-x-1">
                  <Trophy className="h-3 w-3" />
                  <span>{quiz.quiz_data.nrOfQuestions} questions</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatTime(quiz.time_limit_seconds)}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span>Pass: {quiz.passing_score}%</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex-shrink-0 ml-4">
            <Link href={quizUrl}>
              <Button 
                size="sm" 
                variant={quizStatus.status === 'not_attempted' ? 'default' : 'outline'}
                className="min-w-[80px]"
              >
                {quizStatus.status === 'not_attempted' && (
                  <>
                    <Play className="h-3 w-3 mr-1" />
                    Start
                  </>
                )}
                {quizStatus.status === 'passed' && (
                  <>
                    <Trophy className="h-3 w-3 mr-1" />
                    Review
                  </>
                )}
                {quizStatus.status === 'failed' && (
                  <>
                    <RotateCcw className="h-3 w-3 mr-1" />
                    Retry
                  </>
                )}
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 