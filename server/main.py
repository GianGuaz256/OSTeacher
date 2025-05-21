from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
from .routers import courses, lessons # Added lessons router
from .database import supabase # Optional: You might want to initialize DB connection here if needed on startup
# Remove direct crud, models, dependencies imports if they were only for the moved endpoint and not used elsewhere in main.py
# from . import crud, models, dependencies # Potentially remove or prune this
# from .models import CourseCreateRequest, CourseUpdateRequest, CourseCreationResponse, Lesson, UserLessonStatus # Potentially remove or prune this
# from fastapi import FastAPI, HTTPException, Depends, Query # Query might be used elsewhere, others likely not if only for that endpoint
# from supabase import Client # Client might be used elsewhere

app = FastAPI(
    title="Course Management API",
    description="API for creating, reading, and updating courses and managing lessons.", # Updated description
    version="0.1.0",
)

# CORS Middleware Configuration
origins = [
    "http://localhost:3000", # Allow your Next.js frontend
    # You can add other origins here if needed, e.g., your deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, PATCH, etc.)
    allow_headers=["*"], # Allows all headers
)

# Include the course routes
app.include_router(courses.router)
# Include the lessons routes
app.include_router(lessons.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Course Management API"}

# The @app.put("/lessons/{lesson_id}/user-status"...) endpoint definition has been moved to server/routers/lessons.py
# Ensure it's fully removed from here.

# Optional: Add startup/shutdown events if needed
# @app.on_event("startup")
# async def startup_event():
#     # Perform startup tasks, e.g., connecting to DB if not done globally
#     print("Application startup")

# @app.on_event("shutdown")
# async def shutdown_event():
#     # Perform cleanup tasks
#     print("Application shutdown") 