import Link from 'next/link';
import { getAllCourses } from '@/lib/api';
import type { Course } from '@/lib/types';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from 'lucide-react';

export const dynamic = 'force-dynamic'; // Ensure fresh data on each request

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
                <CardTitle className="text-2xl">{course.title}</CardTitle>
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