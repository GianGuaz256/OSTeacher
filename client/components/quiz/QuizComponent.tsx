'use client';

import React, { useState, useEffect } from 'react';
import Quiz from 'react-quiz-component';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, Trophy, Target, RotateCcw, CheckCircle2, XCircle } from 'lucide-react';
import type { QuizData, Quiz as QuizType } from '@/lib/types';

interface QuizComponentProps {
  quiz: QuizType;
  onQuizComplete: (score: number, passed: boolean, timeTaken: number) => void;
  onQuizStart?: () => void;
  onRetry?: () => void;
  className?: string;
}

interface QuizResult {
  numberOfCorrectAnswers: number;
  numberOfIncorrectAnswers: number;
  numberOfQuestions: number;
  questions: Array<{
    question: string;
    correctAnswer: string;
    userAnswer: string;
    isCorrect: boolean;
    point: string;
  }>;
  userInput: string[];
  totalPoints: number;
  correctPoints: number;
}

export default function QuizComponent({ quiz, onQuizComplete, onQuizStart, onRetry, className = '' }: QuizComponentProps) {
  const [timeLeft, setTimeLeft] = useState(quiz.time_limit_seconds);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null);
  const [hasStarted, setHasStarted] = useState(false);

  // Monitor for quiz completion by checking DOM
  useEffect(() => {
    if (!hasStarted || isCompleted) return;

    const checkForCompletion = () => {
      // Look for the quiz result text in the DOM
      const resultText = document.querySelector('.quiz-container')?.textContent;
      if (resultText && resultText.includes('You have completed the quiz')) {
        // Extract score information from the DOM
        const scoreMatch = resultText.match(/You scored (\d+) out of (\d+)/);
        const questionsMatch = resultText.match(/You got (\d+) out of (\d+) questions/);
        
        if (scoreMatch && questionsMatch) {
          const correctPoints = parseInt(scoreMatch[1]);
          const totalPoints = parseInt(scoreMatch[2]);
          const correctAnswers = parseInt(questionsMatch[1]);
          const totalQuestions = parseInt(questionsMatch[2]);
          
          // Create a mock result object
          const mockResult: QuizResult = {
            numberOfCorrectAnswers: correctAnswers,
            numberOfIncorrectAnswers: totalQuestions - correctAnswers,
            numberOfQuestions: totalQuestions,
            correctPoints: correctPoints,
            totalPoints: totalPoints,
            questions: [], // We don't have detailed question data
            userInput: []
          };
          
          handleQuizComplete(mockResult);
        }
      }
    };

    // Check every second for completion
    const interval = setInterval(checkForCompletion, 1000);
    
    return () => clearInterval(interval);
  }, [hasStarted, isCompleted]);

  // Timer effect
  useEffect(() => {
    if (!hasStarted || isCompleted || timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setIsCompleted(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [hasStarted, isCompleted, timeLeft]);

  // Auto-submit when time runs out
  useEffect(() => {
    if (timeLeft === 0 && hasStarted && !isCompleted) {
      handleQuizComplete(null); // Force completion with current answers
    }
  }, [timeLeft, hasStarted, isCompleted]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const handleQuizStart = () => {
    setHasStarted(true);
    setStartTime(Date.now());
    
    // Call onQuizStart to mark quiz as attempted in the database
    if (onQuizStart) {
      onQuizStart();
    }
  };

  const handleQuizComplete = (result: QuizResult | null) => {
    if (isCompleted) {
      return;
    }
    
    setIsCompleted(true);
    const endTime = Date.now();
    const timeTaken = startTime ? Math.floor((endTime - startTime) / 1000) : quiz.time_limit_seconds;
    
    if (result) {
      setQuizResult(result);
      
      // Calculate expected total points from quiz data
      const expectedTotalPoints = quiz.quiz_data.questions.reduce((total, question) => {
        return total + parseInt(question.point || "10", 10);
      }, 0);
      
      // Primary scoring method: Use points-based scoring since quizzes have different point values
      let finalScore: number;
      let totalPointsToUse = result.totalPoints;
      
      // If the library's totalPoints doesn't match our expected total, use our calculation
      if (result.totalPoints !== expectedTotalPoints) {
        totalPointsToUse = expectedTotalPoints;
      }
      
      if (totalPointsToUse > 0) {
        // Use points-based scoring as primary method
        finalScore = (result.correctPoints / totalPointsToUse) * 100;
      } else {
        // Fallback to simple percentage if points are not available
        finalScore = (result.numberOfCorrectAnswers / result.numberOfQuestions) * 100;
      }
      
      const passed = finalScore >= quiz.passing_score;
      
      onQuizComplete(finalScore, passed, timeTaken);
    } else {
      // Time ran out - calculate score based on current state
      const scorePercentage = 0; // No answers submitted
      onQuizComplete(scorePercentage, false, timeTaken);
    }
  };

  const handleRetry = () => {
    setTimeLeft(quiz.time_limit_seconds);
    setStartTime(null);
    setIsCompleted(false);
    setQuizResult(null);
    setHasStarted(false);
    if (onRetry) {
      onRetry();
    }
  };

  const getTimeColor = (): string => {
    const percentage = (timeLeft / quiz.time_limit_seconds) * 100;
    if (percentage > 50) return 'text-green-600';
    if (percentage > 25) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Custom quiz configuration with better styling
  const quizConfig = {
    ...quiz.quiz_data,
    showDefaultResult: true, // Allow default result to show, but we'll still capture the completion
    timer: 0, // Disable built-in timer, we handle our own
    customResultPage: (obj: QuizResult) => {
      // Don't call handleQuizComplete here to avoid double calls
      return <div></div>; // Return empty div to satisfy the type requirement
    },
    onComplete: (obj: QuizResult) => {
      handleQuizComplete(obj);
    },
    // Try additional callback options
    onCompleteAction: (obj: QuizResult) => {
      handleQuizComplete(obj);
    }
  };

  if (!hasStarted) {
    return (
      <div className={`w-full flex justify-center ${className}`}>
        <Card className="w-full max-w-4xl">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold flex items-center justify-center gap-2">
              <Trophy className="h-6 w-6 text-yellow-500" />
              {quiz.quiz_data.quizTitle}
            </CardTitle>
            <p className="text-muted-foreground mt-2">{quiz.quiz_data.quizSynopsis}</p>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div className="flex flex-col items-center space-y-2">
                <Clock className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="font-semibold">Time Limit</p>
                  <p className="text-sm text-muted-foreground">{formatTime(quiz.time_limit_seconds)}</p>
                </div>
              </div>
              <div className="flex flex-col items-center space-y-2">
                <Target className="h-8 w-8 text-green-500" />
                <div>
                  <p className="font-semibold">Passing Score</p>
                  <p className="text-sm text-muted-foreground">{quiz.passing_score}%</p>
                </div>
              </div>
              <div className="flex flex-col items-center space-y-2">
                <Trophy className="h-8 w-8 text-purple-500" />
                <div>
                  <p className="font-semibold">Questions</p>
                  <p className="text-sm text-muted-foreground">{quiz.quiz_data.nrOfQuestions}</p>
                </div>
              </div>
            </div>
            
            <div className="text-center">
              <Button onClick={handleQuizStart} size="lg" className="px-8">
                Start Quiz
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isCompleted && quizResult) {
    // Use the same scoring calculation as in handleQuizComplete
    const expectedTotalPoints = quiz.quiz_data.questions.reduce((total, question) => {
      return total + parseInt(question.point || "10", 10);
    }, 0);
    
    let finalScore: number;
    let totalPointsToUse = quizResult.totalPoints;
    
    // If the library's totalPoints doesn't match our expected total, use our calculation
    if (quizResult.totalPoints !== expectedTotalPoints) {
      totalPointsToUse = expectedTotalPoints;
    }
    
    if (totalPointsToUse > 0) {
      // Use points-based scoring as primary method
      finalScore = (quizResult.correctPoints / totalPointsToUse) * 100;
    } else {
      // Fallback to simple percentage if points are not available
      finalScore = (quizResult.numberOfCorrectAnswers / quizResult.numberOfQuestions) * 100;
    }
    
    const passed = finalScore >= quiz.passing_score;

    return (
      <div className={`w-full flex justify-center ${className}`}>
        <Card className="w-full max-w-4xl">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold flex items-center justify-center gap-2">
              {passed ? (
                <CheckCircle2 className="h-6 w-6 text-green-500" />
              ) : (
                <XCircle className="h-6 w-6 text-red-500" />
              )}
              Quiz {passed ? 'Completed!' : 'Failed'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center">
              <div className={`text-4xl font-bold ${passed ? 'text-green-600' : 'text-red-600'}`}>
                {Math.round(finalScore)}%
              </div>
              <p className="text-muted-foreground">
                {quizResult.numberOfCorrectAnswers} out of {quizResult.numberOfQuestions} correct
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="text-center">
                <Badge variant={passed ? "default" : "destructive"} className="mb-2">
                  {passed ? 'PASSED' : 'FAILED'}
                </Badge>
                <p className="text-sm text-muted-foreground">
                  Required: {quiz.passing_score}%
                </p>
              </div>
              <div className="text-center">
                <Badge variant="outline" className="mb-2">
                  {quizResult.correctPoints} / {totalPointsToUse} points
                </Badge>
                <p className="text-sm text-muted-foreground">
                  Points earned
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="font-semibold text-center">Question Review</h3>
              {quizResult.questions.map((q, index) => (
                <div key={index} className={`p-3 rounded-lg border ${q.isCorrect ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <p className="font-medium mb-2">{q.question}</p>
                  <div className="text-sm space-y-1">
                    <p className={q.isCorrect ? 'text-green-700' : 'text-red-700'}>
                      Your answer: {q.userAnswer}
                    </p>
                    {!q.isCorrect && (
                      <p className="text-green-700">
                        Correct answer: {q.correctAnswer}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center space-x-4">
              {!passed && (
                <Button onClick={handleRetry} variant="outline">
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Retry Quiz
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={`w-full flex justify-center ${className}`}>
      <div className="w-full max-w-4xl">
        {/* Timer and Progress Header */}
        <Card className="mb-4">
          <CardContent className="py-4">
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-2">
                <Clock className={`h-5 w-5 ${getTimeColor()}`} />
                <span className={`font-mono text-lg ${getTimeColor()}`}>
                  {formatTime(timeLeft)}
                </span>
              </div>
              <div className="flex items-center space-x-4">
                <Badge variant="outline">
                  {quiz.quiz_data.quizTitle}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quiz Content with Custom Styling */}
        <div className="quiz-container">
          <style jsx global>{`
            .quiz-container {
              display: flex;
              justify-content: center;
              width: 100%;
            }
            
            .quiz-container > div {
              width: 100%;
              max-width: 100%;
            }
            
            .quiz-container .questionWrapper {
              background: white;
              border-radius: 0.5rem;
              border: 1px solid #e2e8f0;
              padding: 1.5rem;
              margin-bottom: 1rem;
              box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
              width: 100%;
              max-width: 100%;
            }
            
            .quiz-container .question {
              font-size: 1.125rem;
              font-weight: 600;
              margin-bottom: 1rem;
              color: #1f2937;
            }
            
            .quiz-container .answerBtn {
              background: #f8fafc;
              border: 2px solid #e2e8f0;
              border-radius: 0.5rem;
              padding: 0.75rem 1rem;
              margin: 0.5rem 0;
              width: 100%;
              text-align: left;
              transition: all 0.2s;
              cursor: pointer;
            }
            
            .quiz-container .answerBtn:hover {
              background: #f1f5f9;
              border-color: #cbd5e1;
            }
            
            .quiz-container .answerBtn.selected {
              background: #dbeafe;
              border-color: #3b82f6;
              color: #1d4ed8;
            }
            
            .quiz-container .nextQuestionBtn {
              background: #3b82f6;
              color: white;
              border: none;
              border-radius: 0.5rem;
              padding: 0.75rem 1.5rem;
              font-weight: 600;
              cursor: pointer;
              transition: background-color 0.2s;
              margin-top: 1rem;
            }
            
            .quiz-container .nextQuestionBtn:hover {
              background: #2563eb;
            }
            
            .quiz-container .nextQuestionBtn:disabled {
              background: #9ca3af;
              cursor: not-allowed;
            }
            
            .quiz-container .questionModal {
              background: white;
              border-radius: 0.5rem;
              border: 1px solid #e2e8f0;
              box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
              width: 100%;
              max-width: 100%;
            }
            
            .quiz-container .alert {
              border-radius: 0.5rem;
              padding: 1rem;
              margin: 1rem 0;
            }
            
            .quiz-container .alert.alert-success {
              background: #dcfce7;
              border: 1px solid #bbf7d0;
              color: #166534;
            }
            
            .quiz-container .alert.alert-danger {
              background: #fef2f2;
              border: 1px solid #fecaca;
              color: #dc2626;
            }
          `}</style>
          
          <Quiz quiz={quizConfig} shuffle={true} showInstantFeedback={true} />
        </div>
      </div>
    </div>
  );
} 