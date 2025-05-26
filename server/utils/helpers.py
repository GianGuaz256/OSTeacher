import json
import re
from typing import Optional, Dict, Any, List
from ..models import Lesson, LessonStatus, UserLessonStatus

def make_serializable(data):
    """Helper function to make data JSON serializable."""
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

def parse_lesson_external_links(lesson_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Helper function to parse external_links if it's a string."""
    if lesson_data and isinstance(lesson_data.get("external_links"), str):
        try:
            lesson_data["external_links"] = json.loads(lesson_data["external_links"])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse external_links JSON string: '{lesson_data['external_links']}' for lesson {lesson_data.get('id')}. Defaulting to empty list.")
            lesson_data["external_links"] = []
    elif lesson_data and lesson_data.get("external_links") is None:
        lesson_data["external_links"] = []
    return lesson_data

def parse_course_markdown(md_content: str, default_title: str, default_subject: str) -> Dict:
    """
    Helper function to parse Markdown output from the Agno agent.
    This is a simplified parser. For robust production use, consider a dedicated Markdown library
    or instructing the agent to return structured JSON.
    """
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
                    generation_status=LessonStatus.COMPLETED, # Assuming content is present
                    # status (user-facing) will default to UserLessonStatus.NOT_STARTED
                )
            )
    except Exception as e:
        print(f"Error parsing Markdown content: {e}. Using defaults where possible.")
        # Fallback: if parsing fails badly, the raw_generated_content_md will still have the full content.

    return parsed_data

def extract_external_links(content: str) -> List[str]:
    """Extract external links from markdown content."""
    return re.findall(r"\[[^\]]*?\]\(([^)]+?)\)", content) 