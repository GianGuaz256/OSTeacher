from agno.agent import Agent
from agno.tools.wikipedia import WikipediaTools
from agno.models.ollama import Ollama
from agno.models.openai import OpenAIChat
from .model_factory import get_agent_model
from ..utils.retry_utils import retry_api_call, is_retryable_error
import logging

logger = logging.getLogger(__name__)

class CoursePlannerAgent:
    """Agent responsible for planning course structure and outline."""
    
    def __init__(self):
        self.model = get_agent_model()
        self.tools = self._get_tools()
        self.agent = self._create_agent()
    
    def _get_tools(self):
        """Get tools based on model capabilities."""
        # Enable tools for Claude and OpenAI models, disable for Ollama
        use_tools = not isinstance(self.model, Ollama)
        return [WikipediaTools()] if use_tools else []
    
    def _create_agent(self) -> Agent:
        """Create the planner agent with specific configuration."""
        return Agent(
            model=self.model,
            tools=self.tools,
            description="You are an expert AI curriculum designer. Your task is to plan a comprehensive online course.",
            instructions=[
                "Analyze the provided subject, initial title, and difficulty level.",
                "Propose an engaging final course title.",
                "Write a concise and compelling overall course description.",
                "Suggest a single, relevant UTF-8 emoji as the course icon.",
                "Determine the most appropriate field of study from these options: technology, science, mathematics, business, arts, language, health, history, philosophy, engineering, design, music, literature, psychology, economics.",
                "Outline between 5 and 10 lessons (inclusive). For each lesson, provide an 'order' (0-indexed integer), a 'planned_title' (string), a 'planned_description' (1-2 sentence string), and a 'has_quiz' (boolean).",
                "QUIZ STRATEGY: Strategically decide which lessons should have quizzes to reinforce learning:",
                "  - Include quizzes for lessons that introduce key concepts or foundational knowledge",
                "  - Add quizzes after lessons with practical applications or complex topics",
                "  - Generally include quizzes for 40-60% of lessons (not every lesson needs one)",
                "  - Avoid quizzes for purely introductory or concluding lessons unless they contain substantial content",
                "  - Consider the lesson content complexity when deciding on quiz inclusion",
                "IMPORTANT: Keep descriptions brief to avoid response truncation. Each lesson description should be 1-2 sentences maximum.",
                "You MUST output your response exclusively in a valid JSON format as specified in the 'expected_output'. Do not include any other text or explanations before or after the JSON object."
            ],
            expected_output=(
                '{'
                '  "courseTitle": "string",'
                '  "courseDescription": "string",'
                '  "courseIcon": "string (single UTF-8 emoji)",'
                '  "courseField": "string (one of: technology, science, mathematics, business, arts, language, health, history, philosophy, engineering, design, music, literature, psychology, economics)",'
                '  "lesson_outline_plan": ['
                '    { "order": "integer", "planned_title": "string", "planned_description": "string", "has_quiz": "boolean" }'
                '  ]'
                '}'
            ),
            markdown=False,
            reasoning=False,
            show_tool_calls=True,
            add_datetime_to_instructions=True
        )
    
    def _run_agent_with_retry(self, query: str):
        """Run the agent with retry logic for connection errors."""
        def agent_call():
            return self.agent.run(query)
        
        try:
            return retry_api_call(
                agent_call,
                max_retries=3,  # Override default for course planning
                base_delay=2.0,  # Slightly shorter delay for course planning
                backoff_factor=2.0,
                max_delay=20.0
            )
        except Exception as e:
            logger.error(f"Course planning failed after all retries: {e}")
            # Return a structured error response that the service can handle
            class ErrorResponse:
                def __init__(self, error_msg):
                    self.content = None
                    self.error = error_msg
            
            return ErrorResponse(str(e))
    
    def run(self, query: str):
        """Run the planner agent with the given query."""
        logger.info(f"Starting course planning with retry logic")
        return self._run_agent_with_retry(query) 