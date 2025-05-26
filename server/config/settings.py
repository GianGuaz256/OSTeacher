import os
import dotenv
from enum import Enum

dotenv.load_dotenv()

class ModelProvider(str, Enum):
    CLAUDE = "claude"
    OLLAMA = "ollama"

class Settings:
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # AI Models
    AGENT_MODEL_PROVIDER: str = os.getenv("AGENT_MODEL_PROVIDER", "ollama").lower()
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    OLLAMA_MODEL_ID: str = os.getenv("OLLAMA_MODEL_ID", "gemma3:4b")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST")
    
    # Tables
    COURSE_TABLE = "courses"
    LESSONS_TABLE = "lessons"
    
    # Course Generation
    MIN_LESSONS = 5
    MAX_LESSONS = 10
    MIN_SUCCESSFUL_LESSON_RATIO = 0.7
    
    # Claude Model ID
    CLAUDE_MODEL_ID = "claude-3-7-sonnet-20250219"

settings = Settings() 