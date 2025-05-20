'use client';

import { useState } from 'react';
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

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    if (!title.trim() || !subject.trim()) {
      setError("Title and Subject are required.");
      setIsLoading(false);
      return;
    }

    const courseData: CourseCreateRequest = { title, subject, difficulty };

    try {
      const result = await createCourse(courseData);
      if (result && result.id) {
        // Optionally show a success message before redirecting
        router.push('/dashboard');
      } else {
        setError(result?.message || 'Failed to create course. Please try again.');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
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
            disabled={isLoading}
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
            disabled={isLoading}
            required
          />
        </div>
        <div>
          <label htmlFor="difficulty" className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
          <select 
            id="difficulty" 
            value={difficulty} 
            onChange={(e) => setDifficulty(e.target.value as CourseDifficulty)}
            disabled={isLoading}
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

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Creating Course...' : 'Create Course'}
        </Button>
      </form>
       <div className="mt-8 text-center">
        <Button variant="link" onClick={() => router.back()} disabled={isLoading}>
          Cancel
        </Button>
      </div>
    </div>
  );
} 