'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createCourse } from '@/lib/api';
import type { CourseCreateRequest } from '@/lib/types';
import { CourseDifficulty } from '@/lib/types'; // Import enum for difficulty

export default function NewCoursePage() {
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [difficulty, setDifficulty] = useState<CourseDifficulty>(CourseDifficulty.EASY); // Default difficulty
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null); // New state for countdown

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (countdown !== null && countdown > 0) {
      timer = setInterval(() => {
        setCountdown(prevCountdown => (prevCountdown ? prevCountdown - 1 : 0));
      }, 1000);
    } else if (countdown === 0) {
      router.push('/dashboard');
    }
    return () => clearInterval(timer); // Cleanup interval
  }, [countdown, router]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setCountdown(null); // Reset countdown on new submission

    if (!title.trim() || !subject.trim()) {
      setError("Title and Subject are required.");
      setIsLoading(false);
      return;
    }

    const courseData: CourseCreateRequest = { title, subject, difficulty };
    setCountdown(5);
    createCourse(courseData)
  };

  return (
    <div className="container mx-auto p-4 max-w-lg">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-center">Create New Course</h1>
      </header>
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 shadow-md rounded-lg">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">Title</label>
          <Input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Introduction to Web Development"
            disabled={isLoading || countdown !== null}
            required
          />
        </div>
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
          <Input
            id="subject"
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g., Programming"
            disabled={isLoading || countdown !== null}
            required
          />
        </div>
        <div>
          <label htmlFor="difficulty" className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
          <select 
            id="difficulty" 
            value={difficulty} 
            onChange={(e) => setDifficulty(e.target.value as CourseDifficulty)}
            disabled={isLoading || countdown !== null}
            required
            className="block w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {Object.values(CourseDifficulty).map((level) => (
              <option key={level} value={level}>
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <Button type="submit" disabled={isLoading || countdown !== null} className="w-full">
          {countdown !== null
            ? `Redirecting in ${countdown}s...`
            : isLoading
            ? 'Initiating Creation...'
            : 'Create Course'}
        </Button>
      </form>
       <div className="mt-8 text-center">
        <Button variant="link" onClick={() => router.back()} disabled={isLoading || countdown !== null}>
          Cancel
        </Button>
      </div>
    </div>
  );
} 