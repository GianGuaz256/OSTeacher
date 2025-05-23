import Link from 'next/link';
import { getAllCourses } from '@/lib/api';
import type { Course } from '@/lib/types';
import { CourseStatus, UserCourseStatus } from '@/lib/types';
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

export const dynamic = 'force-dynamic'; // Ensure fresh data on each request

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

async function DashboardPage() {
  const courses = await getAllCourses();

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
      
      {(!courses || courses.length === 0) ? (
        <div className="text-center py-10">
          <p className="text-muted-foreground">No courses available at the moment. Click the '+' button to add one!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course: Course) => (
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