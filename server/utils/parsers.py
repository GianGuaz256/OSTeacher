import json
import re
from typing import Dict, Optional

class CourseParser:
    """Parser for AI-generated course plans."""
    
    def parse_course_plan(self, content: str) -> Optional[Dict]:
        """Parse AI-generated course plan from various formats."""
        try:
            # Try to extract JSON from markdown blocks or raw content
            json_string = self._extract_json_string(content)
            if not json_string:
                return None
            
            # Clean and parse JSON
            cleaned_json = self._clean_json_string(json_string)
            return json.loads(cleaned_json)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return None
    
    def _extract_json_string(self, content: str) -> Optional[str]:
        """Extract JSON string from various markdown formats."""
        # Try explicit JSON block
        match = re.search(r"```json\s*([\s\S]+?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try generic code block
        match = re.search(r"```\s*([\s\S]+?)\s*```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try direct JSON object
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        
        # Try to find JSON within content
        match = re.search(r'(\{[\s\S]*\})', content)
        if match:
            return match.group(1)
        
        return None
    
    def _clean_json_string(self, json_string: str) -> str:
        """Clean JSON string of problematic characters."""
        return re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', json_string) 