from agno.agent import Agent
from agno.tools.wikipedia import WikipediaTools
from agno.tools.youtube import YouTubeTools
from agno.models.ollama import Ollama
from agno.models.openai import OpenAIChat
from .model_factory import get_agent_model
from ..utils.retry_utils import retry_api_call, is_retryable_error
import logging

logger = logging.getLogger(__name__)

class LessonContentAgent:
    """Agent responsible for generating detailed lesson content."""
    
    def __init__(self):
        self.model = get_agent_model()
        self.tools = self._get_tools()
        self.agent = self._create_agent()
    
    def _get_tools(self):
        """Get tools based on model capabilities."""
        # Enable tools for Claude and OpenAI models, disable for Ollama
        use_tools = not isinstance(self.model, Ollama)
        return [YouTubeTools(), WikipediaTools()] if use_tools else []
    
    def _create_agent(self) -> Agent:
        """Create the lesson content agent with specific configuration."""
        return Agent(
            model=self.model,
            tools=self.tools,
            description="You are an expert AI content creator, specializing in generating the core teaching material for individual online course lessons.",
            instructions=[
                "Your primary task is to generate the main educational content for a specific online course lesson, given its title, description, the overall course subject, and target difficulty level.",
                "The lesson content MUST be comprehensive enough for approximately 15 minutes of student engagement. This means providing detailed explanations, multiple illustrative examples, and thorough coverage of the lesson's topics.",
                "Structure the lesson clearly with an introduction, the main body of content, and a concluding summary. Use Markdown headings (e.g., ##, ###) appropriately to organize sections within the lesson body.",
                "The output MUST be valid Markdown text, suitable for direct rendering. Ensure all Markdown block elements (paragraphs, lists, code blocks, Mermaid diagrams) are separated by at least one blank line for optimal readability and rendering.",
                "**Content Requirements:**",
                "  - **Detailed Explanations:** Break down complex concepts into understandable parts. Explain the 'why' behind concepts, not just the 'what'.",
                "  - **Practical Code Examples:** If the topic is technical or programming-related, you MUST include relevant code examples in Markdown code blocks (e.g., ```python\\n# Your code here\\nprint('Example')\\n```). Provide at least 2-3 varied code examples where applicable, explaining each one.",
                "  - **Mermaid Diagrams:** To enhance understanding of processes, architectures, relationships, or flowcharts, you MUST include at least one Mermaid diagram within a `mermaid` fenced code block (e.g., ```mermaid\\ngraph TD; A[Concept A] --> B(Concept B);\\n```) where visually appropriate. Explain the diagram.",
                "  - **Illustrative Content:** Use analogies, real-world scenarios, or step-by-step walkthroughs to make the content engaging and easier to grasp.",
                "IMPORTANT: Your response should be ONLY the Markdown content itself. Do NOT include the leading ` ```markdown ` or trailing ` ``` ` delimiters in your output.",
                "Do NOT add any other predefined structural sections like '## Learning Objectives' (unless you deem it a natural part of the introduction), '## Description', etc., beyond the requested intro, body, summary structure.",
                "Do NOT repeat the lesson title as a primary heading (e.g., using `# Lesson Title`) within your generated content; the title is handled externally.",
                "Tailor the depth of explanation, complexity of examples, and language used to the specified overall course subject and difficulty level provided in the query.",
                "Remember, your entire output will be treated as the body of the lesson. Focus on creating rich, detailed, and practical content."
            ],
            markdown=True,
            reasoning=False,
            show_tool_calls=False,
            add_datetime_to_instructions=True
        )
    
    def _run_agent_with_retry(self, query: str):
        """Run the agent with retry logic for connection errors."""
        def agent_call():
            return self.agent.run(query)
        
        try:
            return retry_api_call(
                agent_call,
                max_retries=3,  # Override default for lesson generation
                base_delay=3.0,  # Slightly longer delay for lesson generation
                backoff_factor=2.0,
                max_delay=30.0
            )
        except Exception as e:
            logger.error(f"Lesson content generation failed after all retries: {e}")
            # Return a structured error response that the service can handle
            class ErrorResponse:
                def __init__(self, error_msg):
                    self.content = None
                    self.error = error_msg
            
            return ErrorResponse(str(e))
    
    def run(self, query: str):
        """Run the lesson content agent with the given query."""
        logger.info(f"Starting lesson content generation with retry logic")
        return self._run_agent_with_retry(query) 