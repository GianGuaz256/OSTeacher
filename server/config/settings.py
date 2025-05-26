import os
import dotenv
from enum import Enum
from pathlib import Path

# Get the server directory path and load .env from there
server_dir = Path(__file__).parent.parent
env_path = server_dir / ".env"
dotenv.load_dotenv(env_path)

class ModelProvider(str, Enum):
    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"

class Settings:
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    
    # AI Models
    AGENT_MODEL_PROVIDER: str = os.getenv("AGENT_MODEL_PROVIDER", "openai").lower()
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    OLLAMA_MODEL_ID: str = os.getenv("OLLAMA_MODEL_ID", "gemma3:4b")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL_ID: str = os.getenv("OPENAI_MODEL_ID", "gpt-4.1-mini")
    
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