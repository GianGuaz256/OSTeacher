from supabase import Client
from .models import (
    Course, 
    CourseUpdateRequest,
    Lesson, 
    LessonOutlineItem,
    LessonStatus, 
    CourseDifficulty, 
    CourseStatus,
)
from typing import List, Optional, Dict, Any # Added Any
import uuid
import re
import json  # Added for parsing JSON output from planner agent

# Agno imports
from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.crawl4ai import Crawl4aiTools
from agno.tools.wikipedia import WikipediaTools
from agno.tools.youtube import YouTubeTools
from agno.run.response import RunResponse
from agno.models.ollama import Ollama


# For loading API key from .env
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

COURSE_TABLE = "courses"
LESSONS_TABLE = "lessons" # New table name for lessons
# AGENT_SESSIONS_TABLE = "agent_sessions" # New table name - Removed

from pydantic import ValidationError # Add this import at the top of your file if not already present

# Model Selection Function
def get_agent_model():
    """Determines which LLM to use based on environment variables."""
    provider = os.getenv("AGENT_MODEL_PROVIDER", "claude").lower()
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    if provider == "ollama":
        ollama_model_id = os.getenv("OLLAMA_MODEL_ID")
        if not ollama_model_id:
            print("Warning: AGENT_MODEL_PROVIDER is 'ollama' but OLLAMA_MODEL_ID is not set. Defaulting to 'gemma:latest'. Please set OLLAMA_MODEL_ID.")
            ollama_model_id = "gemma:latest" # A common default, user should verify/change
        
        ollama_host = os.getenv("OLLAMA_HOST") # Optional host
        print(f"Using Ollama model: {ollama_model_id} on host: {ollama_host or 'default'}")
        if ollama_host:
            return Ollama(id=ollama_model_id, host=ollama_host)
        return Ollama(id=ollama_model_id)
    
    elif provider == "claude":
        if not anthropic_api_key:
            raise ValueError("AGENT_MODEL_PROVIDER is 'claude' but ANTHROPIC_API_KEY is not set.")
        # The user previously requested "claude-3-7-sonnet-20250219"
        # We can keep this specific model ID for Claude or make it configurable too.
        # For simplicity, using the last requested Claude model ID directly here.
        claude_model_id = "claude-3-7-sonnet-20250219"
        print(f"Using Claude model: {claude_model_id}")
        return Claude(id=claude_model_id, api_key=anthropic_api_key)
    
    else:
        raise ValueError(f"Unsupported AGENT_MODEL_PROVIDER: {provider}. Choose 'claude' or 'ollama'.")

# Helper function to make data JSON serializable
def make_serializable(data):
    if isinstance(data, list):
        return [make_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: make_serializable(value) for key, value in data.items()}
    elif hasattr(data, '__dict__'): # For custom objects like MessageMetrics
        return make_serializable(vars(data))
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        return str(data) # Fallback to string representation

# Helper function to parse external_links if it's a string
def _parse_lesson_external_links(lesson_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if lesson_data and isinstance(lesson_data.get("external_links"), str):
        try:
            lesson_data["external_links"] = json.loads(lesson_data["external_links"])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse external_links JSON string: '{lesson_data['external_links']}' for lesson {lesson_data.get('id')}. Defaulting to empty list.")
            lesson_data["external_links"] = []
    elif lesson_data and lesson_data.get("external_links") is None:
        lesson_data["external_links"] = []
    return lesson_data

# Helper function to parse Markdown output from the Agno agent
# This is a simplified parser. For robust production use, consider a dedicated Markdown library
# or instructing the agent to return structured JSON.
def _parse_course_markdown(md_content: str, default_title: str, default_subject: str) -> Dict:
    parsed_data = {
        "title": default_title,
        "subject": default_subject,
        "description": f"A course on {default_subject}.", # Default description
        "icon": None,  # Default icon
        "lessons": []
    }

    try:
        # Try to extract overall title
        title_match = re.search(r"^# Course Title: (.*)", md_content, re.MULTILINE)
        if title_match:
            parsed_data["title"] = title_match.group(1).strip()

        # Try to extract overall subject (though it's also an input)
        subject_match = re.search(r"^## Subject: (.*)", md_content, re.MULTILINE)
        if subject_match:
            parsed_data["subject"] = subject_match.group(1).strip() # Overwrite if agent refines it

        # Try to extract course description
        desc_match = re.search(r"\n## Course Description\n(.*?)(?=\n## Lessons|\Z)", md_content, re.DOTALL | re.MULTILINE)
        if desc_match:
            parsed_data["description"] = desc_match.group(1).strip()

        # Try to extract course icon
        icon_match = re.search(r"^## Course Icon: (.*)", md_content, re.MULTILINE)
        if icon_match:
            parsed_data["icon"] = icon_match.group(1).strip()

        # Extract lessons
        # Assumes lessons are structured as: ### Lesson <number>: <Title> \n <Content>
        lesson_content_blocks = md_content.split("## Lessons")[1] if "## Lessons" in md_content else md_content
        
        lesson_pattern = re.compile(r"### Lesson \d+: (.*?)\n(.*?)(?=\n### Lesson \d+:|\Z)", re.DOTALL)
        for match in lesson_pattern.finditer(lesson_content_blocks):
            lesson_title = match.group(1).strip()
            lesson_content_md = match.group(2).strip()
            
            # Attempt to extract external links from lesson_content_md
            # Simple regex for Markdown links: [text](url)
            extracted_links = re.findall(r"\[[^\]]*?]\(([^)]+)\)", lesson_content_md)
            
            parsed_data["lessons"].append(
                Lesson(
                    title=lesson_title, 
                    content_md=lesson_content_md,
                    external_links=extracted_links, # Add extracted links
                    status="pending" # Default status, LessonStatus.PENDING.value could also be used
                )
            )
    except Exception as e:
        print(f"Error parsing Markdown content: {e}. Using defaults where possible.")
        # Fallback: if parsing fails badly, the raw_generated_content_md will still have the full content.

    return parsed_data

def create_course(db: Client, title: str, subject: str, difficulty: str) -> Optional[dict]:
    """
    Generates a course using a two-agent workflow (Planner and Lesson Content agents),
    and saves the course to the database.
    """
    selected_model = get_agent_model() # Get the model instance
    course_id_for_logging = str(uuid.uuid4())

    # Determine if tools should be used based on the model type
    use_tools = not isinstance(selected_model, Ollama)
    print(f"Agent tools will be {'ENABLED' if use_tools else 'DISABLED'} for this run.")

    planner_tools = [Crawl4aiTools(max_length=5), WikipediaTools()] if use_tools else []
    lesson_tools = [YouTubeTools(), Crawl4aiTools(max_length=3), WikipediaTools()] if use_tools else []

    # 1. CoursePlannerAgent Configuration
    planner_agent = Agent(
        model=selected_model,
        tools=planner_tools,
        description="You are an expert AI curriculum designer. Your task is to plan a comprehensive online course.",
        instructions=[
            "Analyze the provided subject, initial title, and difficulty level.",
            "Propose an engaging final course title.",
            "Write a concise and compelling overall course description.",
            "Suggest a single, relevant UTF-8 emoji as the course icon.",
            "Outline between 10 and 15 lessons (inclusive). For each lesson, provide a clear title and a brief 1-2 sentence description of its main topics or learning objectives.",
            "You MUST output your response exclusively in a valid JSON format as specified in the 'expected_output'. Do not include any other text or explanations before or after the JSON object."
        ],
        expected_output=(
            '{\n'
            '  "courseTitle": "string",\n'
            '  "courseDescription": "string",\n'
            '  "courseIcon": "string (single UTF-8 emoji)",\n'
            '  "lessons": [\n'
            '    { "lessonNumber": "integer", "title": "string", "description": "string" }\n'
            '  ]\n'
            '}'
        ),
        markdown=False, # Expecting JSON, not Markdown from planner
        reasoning=False, # Can be true for debugging planner
        show_tool_calls=False, # Keep this false for planner unless debugging
        add_datetime_to_instructions=True
    )

    planner_query = f"Plan a course on '{subject}' titled '{title}' for difficulty '{difficulty}'. Generate 10-15 lessons."
    course_plan_data = None
    planner_response_obj = None

    # Execute CoursePlannerAgent
    try:
        print(f"Running CoursePlannerAgent for: '{title}' on '{subject}'...")
        planner_response_obj = planner_agent.run(planner_query)

        if not isinstance(planner_response_obj, RunResponse):
            print(f"Error: CoursePlannerAgent did not return a RunResponse object. Type: {type(planner_response_obj)}")
            # Try to log whatever response was received
            if planner_response_obj:
                # Create a mock RunResponse-like structure for logging if possible
                mock_response_for_log = type('MockResponse', (object,), {
                    'id': None, 'status': 'ERROR_FORMAT', 'tools': None, 'tool_calls': None,
                    'messages': None, 'error': f'Unexpected response type: {type(planner_response_obj)}',
                    'usage': None, 'content': str(planner_response_obj) # store string representation
                })()
            return None

        planner_content = getattr(planner_response_obj, 'content', None)
        if not planner_content or not isinstance(planner_content, str):
            planner_content = getattr(planner_response_obj, 'text', None) # Fallback
        if not planner_content or not isinstance(planner_content, str):
            planner_content = getattr(planner_response_obj, 'output', None) # Fallback

        if planner_content and isinstance(planner_content, str):
            try:
                # Attempt to find the start and end of the JSON block more robustly
                json_match = re.search(r'\{.*?\}', planner_content, re.DOTALL) # Look for first curly brace to last
                if json_match:
                    json_string_to_parse = json_match.group(0)
                    # Sanitize C0 control characters (including HT, LF, CR) and DEL.
                    json_string_to_parse = re.sub(r'[\x00-\x1F\x7F]', '', json_string_to_parse)
                    course_plan_data = json.loads(json_string_to_parse)
                    
                    # Update the last session data with parsed_output if parsing was successful
                    if planner_response_obj:
                        planner_response_obj["parsed_output"] = make_serializable(course_plan_data) # Ensure serializable
                else:
                    print(f"Error: Could not find a valid JSON block in CoursePlannerAgent output.")
                    print(f"Planner Raw Output (first 500 chars): {planner_content[:500]}...")
                    return None
            except json.JSONDecodeError as e:
                # Provide detailed error information including the problematic string segment
                # e.doc is the input doc to json.loads, e.pos is the index of the error
                context_window = 30 # Show N chars before and after error position
                start_index = max(0, e.pos - context_window)
                end_index = min(len(e.doc), e.pos + context_window)
                error_context = e.doc[start_index:end_index]
                # Escape newlines in context for cleaner log printing
                error_context_escaped = error_context.replace('\n', '\\n').replace('\r', '\\r')

                print(f"Error: Failed to parse JSON output from CoursePlannerAgent. Details below.")
                print(f"  Message: {e.msg}")
                print(f"  At Line: {e.lineno}, Column: {e.colno} (Position: {e.pos})")
                print(f"  Error context (around pos {e.pos}): '...{error_context_escaped}...'")
                print(f"  String attempted for parsing (first 500 chars of sanitized version): ''{json_string_to_parse[:500]}...''")
                print(f"  Original Planner Raw Output (first 500 chars): ''{getattr(planner_response_obj, 'content', '')[:500]}...''")
                return None
        else:
            error_detail = getattr(planner_response_obj, 'error', "No content and no specific error found in response.")
            print(f"Error: CoursePlannerAgent did not provide valid content. Detail: {error_detail}")
            print(f"Planner Response Object: {planner_response_obj}")
            return None

        # Validation for Planner Output
        if not course_plan_data or not isinstance(course_plan_data, dict) or "lessons" not in course_plan_data or not isinstance(course_plan_data["lessons"], list):
            print(f"Error: Invalid course plan structure from CoursePlannerAgent. Plan data: {course_plan_data}")
            return None
        
        num_planned_lessons = len(course_plan_data["lessons"])
        # Adjusted lesson count validation based on typical planner instructions (10-15)
        if not (10 <= num_planned_lessons <= 15):
            print(f"Warning: CoursePlannerAgent planned {num_planned_lessons} lessons, which is outside the instructed range (10-15). Course generation will proceed, but review planner output if this is an issue.")
            # Not returning None, but this could be a stricter check if necessary.
        if num_planned_lessons == 0:
            print("Error: CoursePlannerAgent planned 0 lessons. Aborting.")
            return None

        if not all(isinstance(lesson, dict) and "title" in lesson and "description" in lesson for lesson in course_plan_data["lessons"]):
            print("Error: One or more lessons in the plan are malformed (e.g., missing 'title' or 'description').")
            return None

        print(f"CoursePlannerAgent successfully generated a plan for {num_planned_lessons} lessons.")

    except Exception as e:
        print(f"An unexpected exception occurred during CoursePlannerAgent execution: {e}")
        import traceback
        traceback.print_exc()
        # Log session if planner_response_obj exists and is a RunResponse, otherwise log a generic error session if possible
        agent_name_for_exc_log = "CoursePlannerAgent_Exception"
        response_for_exc_log = planner_response_obj if isinstance(planner_response_obj, RunResponse) else None
        if not response_for_exc_log:
             response_for_exc_log = type('MockResponse', (object,), {
                'id': None, 'status': 'EXCEPTION', 'tools': None, 'tool_calls': None,
                'messages': None, 'error': f'Exception during planner: {str(e)}',
                'usage': None, 'content': traceback.format_exc()
            })()
        # session_to_log related lines removed
        
        return None

    # If course_plan_data is not set after try-except, it means planner failed critically.
    if not course_plan_data:
        print("Critical Error: Course plan data is missing after planner execution block. Aborting. Check logs for earlier errors.")
        return None

    # 2. LessonContentAgent Configuration
    lesson_agent = Agent(
    model=selected_model,
    tools=lesson_tools,
    description="An expert AI content creator specializing in generating comprehensive, engaging, and well-structured educational content for individual online course lessons.",
    instructions=[
        "Generate the core teaching material for a specific online course lesson based on the provided lesson title, description, overall course subject, and target difficulty level.",
        "The lesson content MUST be designed for approximately 15 minutes of student engagement (roughly 1500-2000 words or equivalent in depth, including explanations, examples, and visuals). Ensure the content is comprehensive, covering the topic thoroughly with clear, engaging, and practical material tailored to the specified difficulty level (e.g., beginner, intermediate, advanced).",
        "Output MUST be valid Markdown text, suitable for direct rendering. Ensure all Markdown elements (e.g., paragraphs, lists, code blocks, Mermaid diagrams) are properly formatted with at least one blank line between block elements for optimal readability and rendering.",
        "Structure the lesson with three main sections using Markdown headings (##):",
        "  - **Introduction**: Provide a brief (100-150 words) overview of the lesson's purpose, its relevance to the course, and what students will learn. Engage the reader with a hook (e.g., a question, scenario, or real-world context).",
        "  - **Main Content**: Divide into 2-4 logical subsections (using ### headings) that break down the topic into digestible parts. Each subsection should include detailed explanations and, where relevant, practical examples or visual aids.",
        "  - **Summary**: Conclude with a 100-150 word recap of key points, their importance, and a transition to the next lesson or practical application (e.g., exercises, further reading).",
        "**Content Requirements:**",
        "  - **Detailed Explanations**: Break down concepts into clear, understandable parts. Explain both the 'what' and 'why' to provide context and deepen understanding. Use analogies, real-world scenarios, or step-by-step walkthroughs to make content engaging and relatable.",
        "  - **Practical Examples**: Include 2-3 varied, relevant examples per subsection where applicable. For programming or technical topics, include code examples in Markdown code blocks (e.g., ```python\ncode here\n```) only if directly relevant to the lesson. Ensure code is executable, error-free, and includes comments explaining key lines.",
        "  - **Mermaid Diagrams**: Include a Mermaid diagram in a `mermaid` fenced code block (e.g., ```mermaid\ngraph TD; A-->B;\n```) only when it enhances understanding of processes, relationships, or structures (e.g., workflows, hierarchies, or sequences). Provide a brief explanation of the diagram's purpose and components. Avoid diagrams if they add unnecessary complexity or are not directly relevant.",
        "  - **Engagement**: Use an enthusiastic tone and incorporate relatable analogies or scenarios to maintain student interest. Avoid overly academic or dry language.",
        "**Constraints and Guidelines:**",
        "  - Do NOT include the lesson title as a top-level heading (e.g., `# Lesson Title`) in the output; the title is handled externally.",
        "  - Do NOT include additional predefined sections (e.g., 'Learning Objectives', 'Prerequisites') unless naturally integrated into the introduction or main content.",
        "  - Do NOT use Markdown code block delimiters (e.g., ```markdown) for the overall output; the entire response must be raw Markdown text.",
        "  - Ensure examples and diagrams are directly relevant to the lesson topic and difficulty level, avoiding unnecessary complexity or oversimplification.",
        "  - For non-technical topics, focus on conceptual examples, scenarios, or visual aids instead of code.",
        "  - Validate that the content aligns with the course subject and difficulty, adjusting complexity and depth accordingly (e.g., simpler analogies for beginners, deeper details for advanced).",
        ],
        markdown=True,
        reasoning=False,
        show_tool_calls=False,
        add_datetime_to_instructions=True
    )

    # 3. Iterate and Generate Lessons
    final_lessons_data: List[Lesson] = []
    print(f"Starting generation of {len(course_plan_data['lessons'])} lessons...")

    for i, lesson_plan in enumerate(course_plan_data["lessons"]):
        lesson_title = lesson_plan.get("title", f"Lesson {i+1}")
        lesson_description = lesson_plan.get("description", "No description provided by planner.")
        agent_lesson_name = f"LessonContentAgent_L{i+1}"
        
        print(f"Generating content for Lesson {i+1}: '{lesson_title}'...")
        lesson_query = f"Generate content for lesson '{lesson_title}'. Description: '{lesson_description}'. Overall course subject: '{subject}', Difficulty: '{difficulty}'. Ensure the lesson is comprehensive and engaging."
        lesson_response_obj = None # Initialize for this scope

        try:
            lesson_response_obj = lesson_agent.run(lesson_query)

            if not isinstance(lesson_response_obj, RunResponse):
                print(f"Error: {agent_lesson_name} did not return a RunResponse object. Type: {type(lesson_response_obj)}")
                error_content = f"Error: Agent returned unexpected type: {type(lesson_response_obj)}. Raw response: {str(lesson_response_obj)[:500]}..."
                # Mock response for logging
                mock_response_for_log = type('MockResponse', (object,), {
                    'id': None, 'status': 'ERROR_FORMAT', 'tools': None, 'tool_calls': None,
                    'messages': None, 'error': f'Unexpected response type: {type(lesson_response_obj)}',
                    'usage': None, 'content': str(lesson_response_obj)
                })()
                # session_to_log related lines removed
                final_lessons_data.append(Lesson(title=lesson_title, content_md=error_content, external_links=[], status=LessonStatus.ERROR.value))
                continue # Move to next lesson

            # lesson_session_data related lines removed
            
            lesson_content_md = getattr(lesson_response_obj, 'content', None)
            if not lesson_content_md or not isinstance(lesson_content_md, str):
                 lesson_content_md = getattr(lesson_response_obj, 'text', None)
            if not lesson_content_md or not isinstance(lesson_content_md, str):
                 lesson_content_md = getattr(lesson_response_obj, 'output', None)

            if lesson_content_md and isinstance(lesson_content_md, str) and len(lesson_content_md) > 50: # Basic check for non-empty, meaningful content
                # Corrected regex for Markdown links: [text](url) - captures URL
                extracted_links = re.findall(r'\[[^\]]*?\]\(([^)]+?)\)', lesson_content_md)
                
                lesson_pydantic_obj = Lesson(
                    title=lesson_title, # Use title from plan, agent might refine it in content_md
                    content_md=lesson_content_md,
                    external_links=extracted_links, # Add extracted links
                    status=LessonStatus.PENDING.value
                )
                final_lessons_data.append(lesson_pydantic_obj)
                print(f"Successfully generated content for Lesson {i+1}: '{lesson_title}'")
            else:
                error_msg = f"Error or empty/too short content from {agent_lesson_name} for lesson '{lesson_title}'."
                print(error_msg)
                print(f"Raw content received (first 200 chars): {str(lesson_content_md)[:200]}...")
                lesson_error_detail = getattr(lesson_response_obj, 'error', "No specific error in response, but content invalid.")
                final_lessons_data.append(Lesson(title=lesson_title, content_md=f"{error_msg}\nAgent error detail: {lesson_error_detail}\nRaw output: {str(lesson_content_md)[:200]}...", external_links=[], status=LessonStatus.ERROR.value))
        
        except Exception as e:
            print(f"An unexpected exception occurred during {agent_lesson_name} execution for lesson '{lesson_title}': {e}")
            import traceback
            exc_traceback = traceback.format_exc()
            print(exc_traceback)
            error_content_for_lesson = f"Exception during generation for lesson '{lesson_title}': {e}\nTraceback: {exc_traceback[:1000]}..."
            # Log session if lesson_response_obj exists, otherwise create a mock for logging the exception context
            agent_name_for_lesson_exc_log = f"{agent_lesson_name}_Exception"
            response_for_lesson_exc_log = lesson_response_obj if isinstance(lesson_response_obj, RunResponse) else None
            if not response_for_lesson_exc_log:
                response_for_lesson_exc_log = type('MockResponse', (object,), {
                    'id': None, 'status': 'EXCEPTION', 'tools': None, 'tool_calls': None,
                    'messages': None, 'error': f'Exception during lesson {i+1}: {str(e)}',
                    'usage': None, 'content': exc_traceback
                })()
            # session_to_log related lines removed
            final_lessons_data.append(Lesson(title=lesson_title, content_md=error_content_for_lesson, external_links=[], status=LessonStatus.ERROR.value))
            # Optionally, decide whether to continue or abort course generation if too many lessons fail

    # 4. Validate Generated Lessons
    if not final_lessons_data:
        print("Error: No lessons were processed or generated. Aborting course creation.")
        return None

    successful_lessons_count = sum(1 for lesson in final_lessons_data if lesson.status == LessonStatus.PENDING.value and len(lesson.content_md) > 50)
    min_successful_lessons = max(1, len(course_plan_data["lessons"]) * 0.7) # Ensure at least 1 or 70% successful lessons

    if successful_lessons_count < min_successful_lessons:
        print(f"Error: Failed to generate a sufficient number of successful lessons. Planned: {len(course_plan_data['lessons'])}, Successfully generated: {successful_lessons_count}. Minimum required: {min_successful_lessons:.1f}")
        return None
    
    print(f"Successfully generated {successful_lessons_count} out of {len(course_plan_data['lessons'])} planned lessons meeting quality criteria.")

    # 5. Assemble and Save Course
    new_course_pydantic = Course(
        id=course_id_for_logging, # Use the pre-generated ID
        title=course_plan_data.get("courseTitle", title), # Fallback to original title if planner missed it
        subject=subject, # Keep original subject as it was the basis for planning
        description=course_plan_data.get("courseDescription", f"A comprehensive course on {subject}."),
        icon=course_plan_data.get("courseIcon"),
        difficulty=difficulty,
        lessons=final_lessons_data, # List of Pydantic Lesson objects (includes successful and error ones)
    )

    course_data_to_save = new_course_pydantic.model_dump(exclude_none=True)
    final_course_output = None
    
    try:
        print(f"Saving new course '{new_course_pydantic.title}' (ID: {course_id_for_logging}) to database...")
        response = db.table(COURSE_TABLE).insert(course_data_to_save).execute()

        if response.data and len(response.data) > 0:
            print(f"Successfully created and saved course with ID: {course_id_for_logging}")
            final_course_output = response.data[0]
            
            # pending_agent_sessions saving logic removed
            return final_course_output # Return the saved course data
        else:
            # Handle Supabase V2 error response structure
            error_message = "Unknown error during DB insert for course."
            if hasattr(response, 'error') and response.error:
                error_message = response.error.message
                print(f"DB Error Code: {response.error.code}, Details: {response.error.details}")
            elif hasattr(response, 'status_text'):
                 error_message = f"DB operation failed with status: {response.status_text}"
            
            print(f"Error saving new course to DB: {error_message}")
            if hasattr(response, 'status_code'): print(f"DB op status code: {response.status_code}")
            # pending_agent_sessions saving logic removed
            return None

    except Exception as e:
        print(f"An unexpected exception occurred during DB insert for new course: {e}")
        import traceback
        traceback.print_exc()
        # pending_agent_sessions saving logic removed (around line 555-567 in original)
        return None

def get_course(db: Client, course_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single course by its ID, including its lessons."""
    try:
        course_response = db.table(COURSE_TABLE).select("*").eq("id", course_id).single().execute()
        
        if not course_response.data:
            return None
        
        course_data = course_response.data
        
        lessons_response = db.table(LESSONS_TABLE).select("*").eq("course_id", course_id).order("order_in_course", desc=False).execute()
        
        processed_lessons = []
        if lessons_response.data:
            for lesson_dict in lessons_response.data:
                ext_links_val = lesson_dict.get("external_links")
                if isinstance(ext_links_val, str):
                    try:
                        lesson_dict["external_links"] = json.loads(ext_links_val)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse external_links JSON string: '{ext_links_val}' for lesson {lesson_dict.get('id')}. Defaulting to empty list.")
                        lesson_dict["external_links"] = []
                elif ext_links_val is None: # Handle cases where DB might return None for an empty JSONB
                    lesson_dict["external_links"] = []
                # If it's already a list, Pydantic will handle it.
                
                processed_lessons.append(Lesson(**lesson_dict).model_dump())
        course_data['lessons'] = processed_lessons
        
        # Ensure lesson_outline_plan is parsed if it's a string (though Supabase client usually handles JSONB)
        if isinstance(course_data.get('lesson_outline_plan'), str):
            try:
                course_data['lesson_outline_plan'] = json.loads(course_data['lesson_outline_plan'])
            except json.JSONDecodeError:
                print(f"Warning: Could not parse lesson_outline_plan for course {course_id}")
                course_data['lesson_outline_plan'] = None # Or handle as an error

        return course_data
        
    except Exception as e:
        print(f"An exception occurred while fetching course {course_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_all_courses(db: Client, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves all courses with pagination, including their lessons."""
    try:
        courses_response = db.table(COURSE_TABLE).select("*").range(skip, skip + limit - 1).execute()
        
        if not courses_response.data:
            return []
            
        courses_data = courses_response.data
        course_ids = [course['id'] for course in courses_data]
        
        if not course_ids:
            # Populate lessons as empty list if no courses found (though previous check covers this)
            for course in courses_data:
                course['lessons'] = []
                # Ensure lesson_outline_plan is parsed
                if isinstance(course.get('lesson_outline_plan'), str):
                    try:
                        course['lesson_outline_plan'] = json.loads(course['lesson_outline_plan'])
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse lesson_outline_plan for course {course.get('id')}")
                        course['lesson_outline_plan'] = None
            return courses_data

        all_lessons_response = db.table(LESSONS_TABLE).select("*").in_("course_id", course_ids).order("order_in_course", desc=False).execute()
        
        lessons_by_course_id: Dict[str, List[Dict[str, Any]]] = {}
        if all_lessons_response.data:
            for lesson_dict in all_lessons_response.data:
                course_id_for_lesson = lesson_dict['course_id']
                if course_id_for_lesson not in lessons_by_course_id:
                    lessons_by_course_id[course_id_for_lesson] = []
                
                ext_links_val = lesson_dict.get("external_links")
                if isinstance(ext_links_val, str):
                    try:
                        lesson_dict["external_links"] = json.loads(ext_links_val)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse external_links JSON string: '{ext_links_val}' for lesson {lesson_dict.get('id')}. Defaulting to empty list.")
                        lesson_dict["external_links"] = []
                elif ext_links_val is None: # Handle cases where DB might return None for an empty JSONB
                    lesson_dict["external_links"] = []
                # If it's already a list, Pydantic will handle it.

                lessons_by_course_id[course_id_for_lesson].append(Lesson(**lesson_dict).model_dump())
                
        for course in courses_data:
            course['lessons'] = lessons_by_course_id.get(course['id'], [])
            # Ensure lesson_outline_plan is parsed
            if isinstance(course.get('lesson_outline_plan'), str):
                try:
                    course['lesson_outline_plan'] = json.loads(course['lesson_outline_plan'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse lesson_outline_plan for course {course.get('id')}")
                    course['lesson_outline_plan'] = None
                    
        return courses_data
        
    except Exception as e:
        print(f"An exception occurred while fetching all courses: {e}")
        import traceback
        traceback.print_exc()
        return []

def update_course(db: Client, course_id: str, course_update_request: CourseUpdateRequest) -> Optional[Dict[str, Any]]:
    """Updates an existing course by its ID.
    Handles updates to scalar course fields and the lesson_outline_plan.
    Direct updates to lesson content within this function are discouraged; use regenerate_lesson instead.
    """
    update_data_dict = course_update_request.model_dump(exclude_unset=True)
    
    if not update_data_dict:
        return get_course(db, course_id) # Return existing course if no update data

    # Separate lesson_outline_plan for special handling if it exists
    new_lesson_outline_plan = update_data_dict.pop('lesson_outline_plan', None)

    try:
        # Update scalar fields of the course
        if update_data_dict: # If there are other fields to update besides the plan
            response = db.table(COURSE_TABLE).update(update_data_dict).eq("id", course_id).execute()
            if not response.data and not (response.error is None and response.count == 0): # Check if update failed or course not found
                print(f"Error updating course scalar fields for {course_id}: {response.error}")
                # It might be that the course_id doesn't exist
                existing_course_check = db.table(COURSE_TABLE).select("id").eq("id", course_id).maybe_single().execute()
                if not existing_course_check.data:
                    print(f"Course with id {course_id} not found for update.")
                    return None
                # If course exists but update failed for other reasons, log and potentially return current state or None
                print(f"Course {course_id} exists, but update failed. Current Supabase response: {response}")
                # Depending on strictness, you might return None or the current course data
        
        # Handle lesson_outline_plan update
        if new_lesson_outline_plan is not None:
            print(f"Updating lesson_outline_plan for course {course_id}.")
            # Save the new plan to the course itself
            plan_update_response = db.table(COURSE_TABLE).update({"lesson_outline_plan": new_lesson_outline_plan}).eq("id", course_id).execute()
            if not plan_update_response.data and not (plan_update_response.error is None and plan_update_response.count == 0):
                print(f"Error updating lesson_outline_plan for course {course_id}: {plan_update_response.error}")
                # Potentially return or raise, depending on desired atomicity with lesson recreation

            # Strategy: Delete all existing lessons and recreate them based on the new plan.
            # This is simpler than diffing. For more granular control, separate lesson management endpoints would be better.
            print(f"Deleting existing lessons for course {course_id} before repopulating based on new plan.")
            db.table(LESSONS_TABLE).delete().eq("course_id", course_id).execute() # Add error handling if needed
            
            # Recreate lessons based on the new_lesson_outline_plan
            # This part would be similar to the lesson creation loop in create_course_with_team
            # It involves creating placeholders and then (optionally, synchronously or asynchronously) triggering content generation.
            # For simplicity in this update, we'll create planned lessons. Actual content generation could be a separate step/job.
            
            # Fetch the LessonContentAgent (or pass it) - for now, assume regeneration is manual via new endpoint
            # For this example, we just create lesson placeholders based on the new plan.
            # Full regeneration within update_course can make it very long-running.

            for item_dict in new_lesson_outline_plan:
                lesson_outline = LessonOutlineItem(**item_dict)
                lesson_placeholder_data = {
                    "course_id": course_id,
                    "title": lesson_outline.planned_title,
                    "planned_description": lesson_outline.planned_description,
                    "order_in_course": lesson_outline.order,
                    "status": LessonStatus.PLANNED.value # New lessons start as planned
                }
                insert_lesson_resp = db.table(LESSONS_TABLE).insert(lesson_placeholder_data).execute()
                if not insert_lesson_resp.data:
                    print(f"Error inserting new lesson placeholder for '{lesson_outline.planned_title}' during course update: {insert_lesson_resp.error}")
                    # Decide on error strategy: continue, rollback, or mark course for review

            print(f"Lessons repopulated based on new plan for course {course_id}. Content regeneration may be needed separately.")

        # Fetch and return the updated course with its (potentially new) lessons
        return get_course(db, course_id)
            
    except Exception as e:
        print(f"An exception occurred during course update for {course_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

# Note: Deletion (the 'D' in CRUD) was not requested, but could be added similarly.
# def delete_course(db: Client, course_id: str) -> bool:
#     try:
#         response = db.table(COURSE_TABLE).delete().eq("id", course_id).execute()
#         return len(response.data) > 0 if response.data else False # Check if deletion occurred
#     except Exception as e:
#         print(f"An exception occurred during course deletion for {course_id}: {e}")
#         return False 

def create_course_with_team(db: Client, initial_title: str, subject: str, difficulty: CourseDifficulty) -> Optional[Dict[str, Any]]:
    """
    Generates a course using an Agent Team (Planner and Lesson Content agents),
    saves the course outline, then incrementally creates and generates content for each lesson.
    """
    selected_model = get_agent_model()
    course_id_for_logging = str(uuid.uuid4()) # This will be the actual course ID

    use_tools = not isinstance(selected_model, Ollama)
    print(f"Agent tools will be {'ENABLED' if use_tools else 'DISABLED'} for this run.")

    planner_tools = [Crawl4aiTools(max_length=5), WikipediaTools()] if use_tools else []
    lesson_tools = [YouTubeTools(), Crawl4aiTools(max_length=3), WikipediaTools()] if use_tools else []

    # 1. CoursePlannerAgent Configuration - Updated expected_output
    planner_agent = Agent(
        model=selected_model, 
        tools=planner_tools,
        description="You are an expert AI curriculum designer. Your task is to plan a comprehensive online course.",
        instructions=[
            "Analyze the provided subject, initial title, and difficulty level.",
            "Propose an engaging final course title.",
            "Write a concise and compelling overall course description.",
            "Suggest a single, relevant UTF-8 emoji as the course icon.",
            "Outline between 5 and 10 lessons (inclusive). For each lesson, provide an 'order' (0-indexed integer), a 'planned_title' (string), and a 'planned_description' (1-2 sentence string).", # Adjusted lesson count for faster testing, revert if needed
            "You MUST output your response exclusively in a valid JSON format as specified in the 'expected_output'. Do not include any other text or explanations before or after the JSON object."
        ],
        expected_output=( # Updated expected output for lesson_outline_plan
            '{'
            '  "courseTitle": "string",'
            '  "courseDescription": "string",'
            '  "courseIcon": "string (single UTF-8 emoji)",'
            '  "lesson_outline_plan": ['
            '    { "order": "integer", "planned_title": "string", "planned_description": "string" }'
            '  ]'
            '}'
        ),
        markdown=False,
        reasoning=False,
        show_tool_calls=True,
        add_datetime_to_instructions=True
    )

    planner_query = f"Plan a course on '{subject}' titled '{initial_title}' for difficulty '{difficulty.value}'. Generate 5-10 lessons."
    course_plan_json = None

    try:
        print(f"Running CoursePlannerAgent for: '{initial_title}' on '{subject}'...")
        planner_response_obj = planner_agent.run(planner_query)

        if not isinstance(planner_response_obj, RunResponse) or not planner_response_obj.content:
            error_msg = getattr(planner_response_obj, 'error', "Planner agent did not return a valid RunResponse object or content.")
            print(f"Error: {error_msg}")
            return None

        planner_content_str = planner_response_obj.content
        json_string_to_parse = "" # Initialize to empty string

        try:
            # 1. Try to extract content from ```json ... ``` markdown block
            match_json_block = re.search(r"```json\s*([\s\S]+?)\s*```", planner_content_str, re.DOTALL)
            if match_json_block:
                json_string_to_parse = match_json_block.group(1).strip()
                print(f"Extracted JSON content from explicit '```json ... ```' block.")
            else:
                # 2. Fallback: try to extract from generic ``` ... ``` markdown block
                match_generic_block = re.search(r"```\s*([\s\S]+?)\s*```", planner_content_str, re.DOTALL)
                if match_generic_block:
                    json_string_to_parse = match_generic_block.group(1).strip()
                    print(f"Extracted content from generic '``` ... ```' block (assuming JSON).")
                else:
                    # 3. Fallback: assume the whole string might be JSON or JSON within minimal text.
                    #    Try to find a string that starts with { and ends with } after stripping planner_content_str.
                    #    This is less robust but can catch cases where agent output is almost clean JSON.
                    stripped_content = planner_content_str.strip()
                    if stripped_content.startswith("{") and stripped_content.endswith("}"):
                        json_string_to_parse = stripped_content
                        print(f"Content appears to be a JSON object directly (after stripping wrapper whitespace/text).")
                    else:
                        # 4. Last resort: use the original content string, hoping it's parseable or json.loads will give a good error.
                        json_string_to_parse = planner_content_str 
                        print(f"No markdown fences or clear JSON object found. Attempting to parse the content string as is or find JSON within.")
                        # More aggressive search for a JSON object within the string if it wasn't a clean block
                        json_search_within = re.search(r'({\s*[\s\S]*?\s*})', json_string_to_parse) # Find first { to its corresponding }
                        if json_search_within:
                            json_string_to_parse = json_search_within.group(1)
                            print("Found a JSON-like structure within the content string.")
                        else:
                            print("Could not identify a clear JSON structure even within the content string.")
                            # json_string_to_parse remains as planner_content_str here
            
            if not json_string_to_parse:
                 # This case should ideally not be hit if planner_content_str has content.
                 # If it is, it means all extraction attempts failed to yield a non-empty string.
                 print("Warning: json_string_to_parse is empty after extraction attempts. Using original planner_content_str.")
                 json_string_to_parse = planner_content_str

            # Sanitize C0 control characters from the string that will be parsed
            json_string_to_parse_sanitized = re.sub(r'[\x00-\x1F\x7F]', '', json_string_to_parse)
            
            # Basic check if it looks like a JSON object before parsing
            if not json_string_to_parse_sanitized.strip().startswith("{") or not json_string_to_parse_sanitized.strip().endswith("}"):
                print(f"Warning: String to be parsed does not appear to be a JSON object after extraction/sanitization: ''{json_string_to_parse_sanitized[:200]}...'")
                # Nevertheless, we will attempt to parse it as json.loads() is the ultimate validator.

            course_plan_json = json.loads(json_string_to_parse_sanitized)

        except json.JSONDecodeError as e:
            # Provide detailed error information including the problematic string segment
            # e.doc is the input doc to json.loads, e.pos is the index of the error
            context_window = 30 # Show N chars before and after error position
            start_index = max(0, e.pos - context_window)
            end_index = min(len(e.doc), e.pos + context_window)
            error_context = e.doc[start_index:end_index]
            # Escape newlines in context for cleaner log printing
            error_context_escaped = error_context.replace('\n', '\\n').replace('\r', '\\r')

            print(f"Error: Failed to parse JSON output from CoursePlannerAgent. Details below.")
            print(f"  Message: {e.msg}")
            print(f"  At Line: {e.lineno}, Column: {e.colno} (Position: {e.pos})")
            print(f"  Error context (around pos {e.pos}): '...{error_context_escaped}...'")
            print(f"  String attempted for parsing (first 500 chars of sanitized version): ''{json_string_to_parse_sanitized[:500]}...'")
            print(f"  Original Planner Raw Output (first 500 chars): ''{getattr(planner_response_obj, 'content', '')[:500]}...'")
            return None

        if not course_plan_json or "lesson_outline_plan" not in course_plan_json or not isinstance(course_plan_json["lesson_outline_plan"], list):
            print(f"Error: Invalid course plan structure from CoursePlannerAgent. Plan data: {course_plan_json}")
            return None

        num_planned_lessons = len(course_plan_json["lesson_outline_plan"])
        if not (5 <= num_planned_lessons <= 10): # Ensure this matches instructions
             print(f"Warning: CoursePlannerAgent planned {num_planned_lessons} lessons, outside instructed range. Proceeding.")
        if num_planned_lessons == 0:
            print("Error: CoursePlannerAgent planned 0 lessons. Aborting.")
            return None
        
        # Validate lesson_outline_plan structure
        for i, item_dict in enumerate(course_plan_json["lesson_outline_plan"]):
            try:
                LessonOutlineItem(**item_dict) # Validate each item against the Pydantic model
            except ValidationError as e_val:
                print(f"Error: Invalid item in lesson_outline_plan at index {i}. Validation error details below.")
                print(f"Problematic item_dict: {item_dict}")
                print(f"Pydantic validation errors: {e_val.errors()}") # Detailed error information
                return None
        
        print(f"CoursePlannerAgent successfully generated a plan for {num_planned_lessons} lessons.")

    except Exception as e:
        print(f"An exception occurred during CoursePlannerAgent execution: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 2. Save Initial Course with Outline
    course_data_to_save = {
        "id": course_id_for_logging, # Use the pre-generated UUID
        "title": course_plan_json.get("courseTitle", initial_title),
        "subject": subject,
        "description": course_plan_json.get("courseDescription", f"A course on {subject}."),
        "difficulty": difficulty.value,
        "icon": course_plan_json.get("courseIcon"),
        "lesson_outline_plan": course_plan_json["lesson_outline_plan"], # Save the plan
        "status": CourseStatus.DRAFT.value, # Initial status
        # "level": None, # Or some default
    }

    try:
        course_insert_response = db.table(COURSE_TABLE).insert(course_data_to_save).execute()
        if not course_insert_response.data:
            print(f"Error: Failed to insert initial course data. Response: {course_insert_response.error}")
            return None
        created_course_id = course_insert_response.data[0]['id']
        print(f"Successfully saved initial course with ID: {created_course_id}")
    except Exception as e:
        print(f"Exception saving initial course: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 3. LessonContentAgent Configuration
    lesson_agent = Agent(
        model=selected_model, 
        tools=lesson_tools,
        description="You are an expert AI content creator, specializing in generating the core teaching material for individual online course lessons.", # Keep your detailed description
        instructions=[ # Keep your detailed instructions for lesson content generation
            "Your primary task is to generate the main educational content for a specific online course lesson, given its title, description, the overall course subject, and target difficulty level.",
            "The lesson content MUST be comprehensive enough for approximately 15 minutes of student engagement. This means providing detailed explanations, multiple illustrative examples, and thorough coverage of the lesson\'s topics.",
            "Structure the lesson clearly with an introduction, the main body of content, and a concluding summary. Use Markdown headings (e.g., ##, ###) appropriately to organize sections within the lesson body.",
            "The output MUST be valid Markdown text, suitable for direct rendering. Ensure all Markdown block elements (paragraphs, lists, code blocks, Mermaid diagrams) are separated by at least one blank line for optimal readability and rendering.",
            "**Content Requirements:**",
            "  - **Detailed Explanations:** Break down complex concepts into understandable parts. Explain the \'why\' behind concepts, not just the \'what\'.",
            "  - **Practical Code Examples:** If the topic is technical or programming-related, you MUST include relevant code examples in Markdown code blocks (e.g., ```python\n# Your code here\nprint(\'Example\')\n```). Provide at least 2-3 varied code examples where applicable, explaining each one.",
            "  - **Mermaid Diagrams:** To enhance understanding of processes, architectures, relationships, or flowcharts, you MUST include at least one Mermaid diagram within a `mermaid` fenced code block (e.g., ```mermaid\ngraph TD; A[Concept A] --> B(Concept B);\n```) where visually appropriate. Explain the diagram.",
            "  - **Illustrative Content:** Use analogies, real-world scenarios, or step-by-step walkthroughs to make the content engaging and easier to grasp.",
            "IMPORTANT: Your response should be ONLY the Markdown content itself. Do NOT include the leading ` ```markdown ` or trailing ` ``` ` delimiters in your output.",
            "Do NOT add any other predefined structural sections like \'## Learning Objectives\' (unless you deem it a natural part of the introduction), \'## Description\', etc., beyond the requested intro, body, summary structure.",
            "Do NOT repeat the lesson title as a primary heading (e.g., using `# Lesson Title`) within your generated content; the title is handled externally.",
            "Tailor the depth of explanation, complexity of examples, and language used to the specified overall course subject and difficulty level provided in the query.",
            "Remember, your entire output will be treated as the body of the lesson. Focus on creating rich, detailed, and practical content."
        ],
        markdown=True,
        reasoning=False,
        show_tool_calls=False,
        add_datetime_to_instructions=True
    )

    # 4. Iterate, Create Lesson Placeholders, Generate Content, and Update Lessons
    # final_lessons_data: List[Lesson] = [] # No longer needed here, we fetch at the end.

    for lesson_outline_item_dict in course_plan_json["lesson_outline_plan"]:
        lesson_outline = LessonOutlineItem(**lesson_outline_item_dict) # Parse to Pydantic model

        lesson_placeholder_data = {
            "course_id": created_course_id,
            "title": lesson_outline.planned_title,
            "planned_description": lesson_outline.planned_description,
            "order_in_course": lesson_outline.order,
            "status": LessonStatus.PLANNED.value 
        }
        
        try:
            print(f"Creating placeholder for lesson: '{lesson_outline.planned_title}'")
            placeholder_response = db.table(LESSONS_TABLE).insert(lesson_placeholder_data).execute()
            if not placeholder_response.data or not placeholder_response.data[0].get('id'):
                print(f"Error creating placeholder for lesson '{lesson_outline.planned_title}'. Response: {placeholder_response.error}")
                # Decide if to continue with next lesson or abort. For now, continue.
                continue

            lesson_id = placeholder_response.data[0]['id']
            print(f"Placeholder lesson created with ID: {lesson_id}")

            # Update status to 'generating' before calling agent
            db.table(LESSONS_TABLE).update({"status": LessonStatus.GENERATING.value}).eq("id", lesson_id).execute()

            print(f"Generating content for lesson: '{lesson_outline.planned_title}' (ID: {lesson_id})")
            lesson_content_query = (
                f"Lesson Title: {lesson_outline.planned_title}\\n"
                f"Lesson Description: {lesson_outline.planned_description}\\n"
                f"Overall Course Subject: {subject}\\n"
                f"Overall Course Difficulty: {difficulty.value}"
            )
            
            lesson_content_response = lesson_agent.run(lesson_content_query)
            
            if lesson_content_response and lesson_content_response.content:
                # Extract links (simple regex for Markdown links)
                extracted_links = re.findall(r"\[[^\]]*?\]\(([^)]+?)\)", lesson_content_response.content)
                
                lesson_update_data = {
                    "content_md": lesson_content_response.content,
                    "external_links": json.dumps(extracted_links), # Ensure it's a JSON string for Supabase JSONB
                    "status": LessonStatus.COMPLETED.value
                }
                db.table(LESSONS_TABLE).update(lesson_update_data).eq("id", lesson_id).execute()
                print(f"Content generated and saved for lesson ID: {lesson_id}")
            else:
                print(f"Failed to generate content for lesson ID: {lesson_id}. Error: {getattr(lesson_content_response, 'error', 'No content')}")
                db.table(LESSONS_TABLE).update({"status": LessonStatus.GENERATION_FAILED.value}).eq("id", lesson_id).execute()
        
        except Exception as e_lesson:
            print(f"Exception during lesson processing for '{lesson_outline.planned_title}': {e_lesson}")
            import traceback
            traceback.print_exc()
            if 'lesson_id' in locals(): # If placeholder was created, mark as failed
                 db.table(LESSONS_TABLE).update({"status": LessonStatus.GENERATION_FAILED.value}).eq("id", lesson_id).execute()
            # Continue to the next lesson
            continue

    # 5. Return the full course data by fetching it using get_course
    # This ensures the response includes the generated lessons list and is consistent.
    print(f"Course creation process finished for course ID: {created_course_id}. Fetching complete data...")
    return get_course(db, created_course_id)

def regenerate_lesson(db: Client, lesson_id: str) -> Optional[Dict[str, Any]]:
    """Regenerates the content for a specific lesson using the LessonContentAgent."""
    try:
        # 1. Fetch the lesson to regenerate
        # Ensure 'courses' is the correct relationship name for the join.
        # It might be 'course:courses(id, subject, difficulty)' or similar depending on FK naming.
        # For simplicity, assuming 'courses(subject, difficulty)' works as intended by Supabase client for a join.
        lesson_response = db.table(LESSONS_TABLE).select("*, courses(id, subject, difficulty)").eq("id", lesson_id).maybe_single().execute()
        
        if not lesson_response.data:
            print(f"Lesson with ID {lesson_id} not found for regeneration.")
            return None # Explicitly return None if lesson not found
    
        lesson_data = lesson_response.data
        current_lesson_title = lesson_data.get('title')
        planned_description = lesson_data.get('planned_description') # Description from the initial plan
        
        course_info = lesson_data.get('courses') # This should be the joined course data

        if not isinstance(course_info, dict): # If 'courses' is not a dict (e.g., just an ID or None)
            course_id_from_lesson = lesson_data.get('course_id')
            if not course_id_from_lesson:
                print(f"Error: Lesson {lesson_id} has no course_id and course data was not joined correctly.")
                # Update lesson status to reflect this critical error
                db.table(LESSONS_TABLE).update({
                    "status": LessonStatus.GENERATION_FAILED.value,
                    "content_md": "Regeneration failed: Missing course association."
                }).eq("id", lesson_id).execute()
                return None

            print(f"Course data not fully joined for lesson {lesson_id}. Fetching course {course_id_from_lesson} separately.")
            parent_course_response = db.table(COURSE_TABLE).select("id, subject, difficulty").eq("id", course_id_from_lesson).maybe_single().execute()
            if not parent_course_response.data:
                print(f"Error: Parent course {course_id_from_lesson} not found for lesson {lesson_id}.")
                db.table(LESSONS_TABLE).update({
                    "status": LessonStatus.GENERATION_FAILED.value,
                    "content_md": "Regeneration failed: Parent course not found."
                }).eq("id", lesson_id).execute()
                return None
            course_info = parent_course_response.data

        if not course_info or not course_info.get('subject') or not course_info.get('difficulty'):
            print(f"Error: Critical course information (subject or difficulty) is missing for lesson {lesson_id}. Course info: {course_info}")
            db.table(LESSONS_TABLE).update({
                "status": LessonStatus.GENERATION_FAILED.value,
                "content_md": "Regeneration failed: Course subject/difficulty missing."
            }).eq("id", lesson_id).execute()
            return None

        course_subject = course_info.get('subject')
        course_difficulty_str = course_info.get('difficulty')
        
        try:
            # Use .value if CourseDifficulty is an Enum, otherwise it's a string
            course_difficulty_enum_val = CourseDifficulty(course_difficulty_str).value if course_difficulty_str else CourseDifficulty.MEDIUM.value
        except ValueError:
            print(f"Warning: Invalid course difficulty '{course_difficulty_str}' for lesson {lesson_id}. Defaulting to MEDIUM.")
            course_difficulty_enum_val = CourseDifficulty.MEDIUM.value

        # 2. Update lesson status to 'generating' and clear old content/links
        db.table(LESSONS_TABLE).update({
            "status": LessonStatus.GENERATING.value, 
            "content_md": "Generating new content...",
            "external_links": json.dumps([]) # Clear previous links
        }).eq("id", lesson_id).execute()
        print(f"Set status to 'generating' for lesson ID: {lesson_id}")

        # 3. Get AI model and configure LessonContentAgent
        selected_model = get_agent_model()
        use_tools = not isinstance(selected_model, Ollama)
        lesson_tools = [YouTubeTools(), Crawl4aiTools(max_length=3), WikipediaTools()] if use_tools else []

        lesson_agent = Agent(
            model=selected_model,
            tools=lesson_tools,
            description="You are an expert AI content creator, specializing in generating the core teaching material for individual online course lessons.", # Same description as in create_course
            instructions=[ # Same instructions as in create_course_with_team's lesson_agent
                "Your primary task is to generate the main educational content for a specific online course lesson, given its title, description, the overall course subject, and target difficulty level.",
                "The lesson content MUST be comprehensive enough for approximately 15 minutes of student engagement. This means providing detailed explanations, multiple illustrative examples, and thorough coverage of the lesson\'s topics.",
                "Structure the lesson clearly with an introduction, the main body of content, and a concluding summary. Use Markdown headings (e.g., ##, ###) appropriately to organize sections within the lesson body.",
                "The output MUST be valid Markdown text, suitable for direct rendering. Ensure all Markdown block elements (paragraphs, lists, code blocks, Mermaid diagrams) are separated by at least one blank line for optimal readability and rendering.",
                "**Content Requirements:**",
                "  - **Detailed Explanations:** Break down complex concepts into understandable parts. Explain the \'why\' behind concepts, not just the \'what\'.",
                "  - **Practical Code Examples:** If the topic is technical or programming-related, you MUST include relevant code examples in Markdown code blocks (e.g., ```python\n# Your code here\nprint(\'Example\')\n```). Provide at least 2-3 varied code examples where applicable, explaining each one.",
                "  - **Mermaid Diagrams:** To enhance understanding of processes, architectures, relationships, or flowcharts, you MUST include at least one Mermaid diagram within a `mermaid` fenced code block (e.g., ```mermaid\ngraph TD; A[Concept A] --> B(Concept B);\n```) where visually appropriate. Explain the diagram.",
                "  - **Illustrative Content:** Use analogies, real-world scenarios, or step-by-step walkthroughs to make the content engaging and easier to grasp.",
                "IMPORTANT: Your response should be ONLY the Markdown content itself. Do NOT include the leading ` ```markdown ` or trailing ` ``` ` delimiters in your output.",
                "Do NOT add any other predefined structural sections like \'## Learning Objectives\' (unless you deem it a natural part of the introduction), \'## Description\', etc., beyond the requested intro, body, summary structure.",
                "Do NOT repeat the lesson title as a primary heading (e.g., using `# Lesson Title`) within your generated content; the title is handled externally.",
                "Tailor the depth of explanation, complexity of examples, and language used to the specified overall course subject and difficulty level provided in the query.",
                "Remember, your entire output will be treated as the body of the lesson. Focus on creating rich, detailed, and practical content."
            ],
            markdown=True, # Agno should handle stripping of ```markdown if agent still adds it
            reasoning=False, 
            show_tool_calls=False,
            add_datetime_to_instructions=True
        )

        # 4. Construct query and run agent
        lesson_content_query = (
            f"Lesson Title: {current_lesson_title}\\n"
            f"Lesson Description: {planned_description or 'No specific planned description available.'}\\n"
            f"Overall Course Subject: {course_subject}\\n"
            f"Overall Course Difficulty: {course_difficulty_enum_val}"
        )
        
        print(f"Generating content for lesson: '{current_lesson_title}' (ID: {lesson_id})")
        lesson_content_response = lesson_agent.run(lesson_content_query)
        
        # 5. Process response and update lesson
        if lesson_content_response and hasattr(lesson_content_response, 'content') and \
           lesson_content_response.content and isinstance(lesson_content_response.content, str):
            
            extracted_links = re.findall(r"\[[^\]]*?\]\(([^)]+?)\)", lesson_content_response.content)
            
            lesson_update_data = {
                "content_md": lesson_content_response.content,
                "external_links": json.dumps(extracted_links), 
                "status": LessonStatus.COMPLETED.value
            }
            update_response = db.table(LESSONS_TABLE).update(lesson_update_data).eq("id", lesson_id).execute()

            if update_response.data:
                print(f"Content successfully regenerated and saved for lesson ID: {lesson_id}")
                return _parse_lesson_external_links(update_response.data[0]) 
            else:
                db_error_message = "Unknown DB error during update."
                if update_response.error:
                    db_error_message = f"Code: {update_response.error.code}, Message: {update_response.error.message}"
                print(f"Failed to save regenerated content for lesson ID: {lesson_id}. DB Error: {db_error_message}")
                # Update status to failed, but keep the (unsaved) generated content for inspection if needed, or a specific error message.
                db.table(LESSONS_TABLE).update({
                    "status": LessonStatus.GENERATION_FAILED.value, 
                    "content_md": f"Failed to save after regeneration. DB Error: {db_error_message}. \\nOriginal generated content (first 200 chars): {lesson_content_response.content[:200]}..."
                }).eq("id", lesson_id).execute()
                # Fetch the lesson to return its current (failed) state
                failed_lesson_state_response = db.table(LESSONS_TABLE).select("*").eq("id", lesson_id).maybe_single().execute()
                return _parse_lesson_external_links(failed_lesson_state_response.data if failed_lesson_state_response.data else None)
        else:
            agent_error_msg = "Agent returned no content or an invalid response."
            if lesson_content_response and hasattr(lesson_content_response, 'error') and lesson_content_response.error:
                agent_error_msg = str(lesson_content_response.error)
            elif not lesson_content_response:
                agent_error_msg = "Agent did not return a response object."
            
            print(f"Failed to generate content for lesson ID: {lesson_id}. Agent Error: {agent_error_msg}")
            db.table(LESSONS_TABLE).update({
                "status": LessonStatus.GENERATION_FAILED.value,
                "content_md": f"Content generation failed. Agent error: {agent_error_msg}"
            }).eq("id", lesson_id).execute()
            failed_lesson_state_response = db.table(LESSONS_TABLE).select("*").eq("id", lesson_id).maybe_single().execute()
            return _parse_lesson_external_links(failed_lesson_state_response.data if failed_lesson_state_response.data else None)

    except Exception as e:
        print(f"An unexpected exception occurred during lesson regeneration for ID {lesson_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Attempt to update lesson status to reflect failure due to exception, if lesson_id is known
        if 'lesson_id' in locals() and lesson_id:
            try:
                db.table(LESSONS_TABLE).update({
                    "status": LessonStatus.GENERATION_FAILED.value,
                    "content_md": f"Critical exception during regeneration: {str(e)[:500]}"
                }).eq("id", lesson_id).execute()
            except Exception as db_update_err:
                print(f"Additionally, failed to update lesson status to FAILED after critical exception: {db_update_err}")
        
        return None
# End of the regenerate_lesson function.
# The file might end here if regenerate_lesson was the last function.
# If there's more code below this in your actual file, it's not part of this edit.
