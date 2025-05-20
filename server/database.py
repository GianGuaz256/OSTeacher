import os
from supabase import create_client, Client
from typing import Optional
import dotenv
from pathlib import Path

# Determine the path to the .env file relative to this script
current_dir = Path(__file__).parent
dotenv_path = current_dir / ".env"

# Load environment variables from .env file
dotenv.load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY")

supabase: Optional[Client] = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("WARNING: Supabase URL or Key not set in environment variables. Supabase client not initialized.")

def get_db():
    # Optional: Add a check here to ensure supabase is initialized if needed
    # if supabase is None:
    #     raise RuntimeError("Supabase client is not initialized. Check environment variables.")
    return supabase 