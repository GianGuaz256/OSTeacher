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

4.  **Configure Supabase:**
    *   Create a `.env` file in the `server` directory (`server/.env`).
    *   Add your Supabase project URL and anon key to the `.env` file:
        ```dotenv
        SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL
        SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
        ```
    *   **Important:** Ensure you have a table named `courses` in your Supabase project with columns corresponding to the `Course` model defined in `models.py`. You might need to adjust the Supabase table schema (e.g., use UUID for `id`, handle JSONB for `lessons`).
        *   `id` (uuid, primary key)
        *   `title` (text)
        *   `lessons` (jsonb - an array of lesson objects)
        *   `duration` (text)
        *   `level` (text - matching CourseLevel enum)
        *   `status` (text - matching CourseStatus enum)

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