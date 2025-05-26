# Course Management API Server

This directory contains a FastAPI server for managing courses using Supabase as the database.

## Setup

1.  **Navigate to the server directory:**
    ```bash
    cd server
    ```

2.  **Create a Python virtual environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create a `.env` file in the `server` directory (`server/.env`).
    *   Add your configuration to the `.env` file:
        ```dotenv
        # Database Configuration
        SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL
        SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
        
        # AI Model Configuration
        AGENT_MODEL_PROVIDER=openai  # Options: openai, claude, ollama
        
        # OpenAI Configuration (if using OpenAI)
        OPENAI_API_KEY=YOUR_OPENAI_API_KEY
        OPENAI_MODEL_ID=gpt-4.1-mini  # Default: gpt-4.1-mini, can use gpt-4o, gpt-4, etc.
        
        # Anthropic Configuration (if using Claude)
        ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
        
        # Ollama Configuration (if using Ollama)
        OLLAMA_MODEL_ID=gemma3:4b  # Default model
        OLLAMA_HOST=http://localhost:11434  # Optional, defaults to localhost
        ```

5.  **Configure Supabase Database:**
    *   **Important:** Ensure you have a table named `courses` in your Supabase project with columns corresponding to the `Course` model defined in `models.py`. You might need to adjust the Supabase table schema (e.g., use UUID for `id`, handle JSONB for `lessons`).
        *   `id` (uuid, primary key)
        *   `title` (text)
        *   `lessons` (jsonb - an array of lesson objects)
        *   `duration` (text)
        *   `level` (text - matching CourseLevel enum)
        *   `status` (text - matching CourseStatus enum)

## AI Model Providers

The system supports three AI model providers:

### OpenAI (Recommended)
- **Model**: GPT-4.1-mini (default), GPT-4o, GPT-4, etc.
- **Features**: Fast, reliable, supports tools and structured outputs
- **Configuration**: Set `AGENT_MODEL_PROVIDER=openai` and `OPENAI_API_KEY`

### Anthropic Claude
- **Model**: Claude-3-7-sonnet-20250219
- **Features**: High-quality outputs, good reasoning capabilities
- **Configuration**: Set `AGENT_MODEL_PROVIDER=claude` and `ANTHROPIC_API_KEY`

### Ollama (Local)
- **Model**: Configurable local models (default: gemma3:4b)
- **Features**: Local inference, no API costs, tools disabled for performance
- **Configuration**: Set `AGENT_MODEL_PROVIDER=ollama` and ensure Ollama is running

## Running the Server

From the `server` directory, run the following command:

```bash
uvicorn main:app --reload
```

*   `main`: refers to the `main.py` file.
*   `app`: refers to the `FastAPI()` instance created inside `main.py`.
*   `--reload`: enables auto-reloading when code changes (useful for development).

The API will be available at `http://127.0.0.1:8000`.
You can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`. 