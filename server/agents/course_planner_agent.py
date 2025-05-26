from agno.agent import Agent
from agno.tools.wikipedia import WikipediaTools
from agno.models.ollama import Ollama
from .model_factory import get_agent_model

class CoursePlannerAgent:
    """Agent responsible for planning course structure and outline."""
    
    def __init__(self):
        self.model = get_agent_model()
        self.tools = self._get_tools()
        self.agent = self._create_agent()
    
    def _get_tools(self):
        """Get tools based on model capabilities."""
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
                "Outline between 5 and 10 lessons (inclusive). For each lesson, provide an 'order' (0-indexed integer), a 'planned_title' (string), and a 'planned_description' (1-2 sentence string).",
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
                '    { "order": "integer", "planned_title": "string", "planned_description": "string" }'
                '  ]'
                '}'
            ),
            markdown=False,
            reasoning=False,
            show_tool_calls=True,
            add_datetime_to_instructions=True
        )
    
    def run(self, query: str):
        """Run the planner agent with the given query."""
        return self.agent.run(query) 