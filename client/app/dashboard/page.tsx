'use client';

import Link from 'next/link';
import { getAllCourses } from '@/lib/api';
import type { Course } from '@/lib/types';
import { CourseStatus, UserCourseStatus, CourseField, getFieldEmoji, getFieldDisplayName } from '@/lib/types';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus } from 'lucide-react';
import { useState, useEffect } from 'react';

// Helper function to determine badge variant based on course status
const getStatusBadgeVariant = (status: UserCourseStatus | string | undefined) => {
  if (!status) return "secondary";
  switch (status.toLowerCase()) {
    case UserCourseStatus.COMPLETED.toLowerCase():
      return "success";
    case UserCourseStatus.IN_PROGRESS.toLowerCase():
      return "warning";
    case UserCourseStatus.NOT_STARTED.toLowerCase():
      return "outline";
    default:
      return "secondary";
  }
};

function DashboardPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [filteredCourses, setFilteredCourses] = useState<Course[]>([]);
  const [selectedField, setSelectedField] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const coursesData = await getAllCourses();
        setCourses(coursesData);
        setFilteredCourses(coursesData);
      } catch (error) {
        console.error('Error fetching courses:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, []);

  useEffect(() => {
    if (selectedField === 'all') {
      setFilteredCourses(courses);
    } else {
      setFilteredCourses(courses.filter(course => course.field === selectedField));
    }
  }, [selectedField, courses]);

  // Get unique fields from courses
  const availableFields = Array.from(new Set(courses.map(course => course.field).filter(Boolean)));

  // Get all possible fields for the selector (even if no courses exist for them yet)
  const allFields = Object.values(CourseField);

  if (loading) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center py-10">
          <p className="text-muted-foreground">Loading courses...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <header className="mb-8 flex justify-between items-center">
        <h1 className="text-4xl font-bold tracking-tight">Available Courses</h1>
        <Link href="/courses/new" passHref>
          <Button variant="outline" size="icon">
            <Plus className="h-4 w-4" />
            <span className="sr-only">Add new course</span>
          </Button>
        </Link>
      </header>
      
      {/* Field Selector */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Filter by Field</h2>
        <div className="flex flex-wrap gap-3">
          {/* All Fields Button */}
          <Button
            variant={selectedField === 'all' ? 'default' : 'outline'}
            onClick={() => setSelectedField('all')}
            className="h-auto py-1 px-6 flex items-center gap-3 rounded-full min-w-[140px]"
          >
            <span className="text-xl">📚</span>
            <div className="flex flex-col items-start">
              <span className="text-sm font-medium">All Fields</span>
              <span className="text-xs text-muted-foreground">
                {courses.length} courses
              </span>
            </div>
          </Button>

          {/* Individual Field Buttons */}
          {allFields.map((field) => {
            const coursesInField = courses.filter(course => course.field === field);
            const hasCoursesInField = coursesInField.length > 0;
            
            return (
              <Button
                key={field}
                variant={selectedField === field ? 'default' : 'outline'}
                onClick={() => setSelectedField(field)}
                disabled={!hasCoursesInField}
                className={`h-auto py-1 px-6 flex items-center gap-3 rounded-full min-w-[140px] ${
                  !hasCoursesInField ? 'opacity-50' : ''
                }`}
              >
                <span className="text-xl">{getFieldEmoji(field)}</span>
                <div className="flex flex-col items-start">
                  <span className="text-sm font-medium">{getFieldDisplayName(field)}</span>
                  <span className="text-xs text-muted-foreground">
                    {coursesInField.length} course{coursesInField.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </Button>
            );
          })}
        </div>
      </div>
      
      {/* Courses Grid */}
      {(!filteredCourses || filteredCourses.length === 0) ? (
        <div className="text-center py-10">
          <p className="text-muted-foreground">
            {selectedField === 'all' 
              ? "No courses available at the moment. Click the '+' button to add one!"
              : `No courses found for ${getFieldDisplayName(selectedField)}. Try selecting a different field or add a new course!`
            }
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCourses.map((course: Course) => (
            <Card key={course.id} className="flex flex-col">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <CardTitle className="text-2xl">{course.title}</CardTitle>
                  {course.status && course.generation_status !== CourseStatus.DRAFT && (
                    <Badge variant={getStatusBadgeVariant(course.status)} className="ml-2 whitespace-nowrap">
                      {course.status.replace('_', ' ')}
                    </Badge>
                  )}
                </div>
                <CardDescription>{course.subject}</CardDescription>
                {course.field && (
                  <Badge variant="outline" className="w-fit">
                    <span className="mr-1">{getFieldEmoji(course.field)}</span>
                    {getFieldDisplayName(course.field)}
                  </Badge>
                )}
              </CardHeader>
              <CardContent className="flex-grow">
                <p className="text-sm text-muted-foreground line-clamp-3">{course.description}</p>
                {course.difficulty && (
                  <p className="text-xs mt-2">
                    Difficulty: <span className="font-semibold">{course.difficulty.toUpperCase()}</span>
                  </p>
                )}
                 {course.icon && <p className="text-2xl mt-2">{course.icon}</p>}
              </CardContent>
              <CardFooter>
                <Link href={`/courses/${course.id}`} className="w-full" passHref>
                  <Button className="w-full">
                    View Course
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default DashboardPage; 