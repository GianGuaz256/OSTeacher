from agno.agent import Agent
from agno.tools.wikipedia import WikipediaTools
from agno.models.ollama import Ollama
from agno.models.openai import OpenAIChat
from .model_factory import get_agent_model
from ..utils.retry_utils import retry_api_call, is_retryable_error
import logging

logger = logging.getLogger(__name__)

class QuizGeneratorAgent:
    """Agent responsible for generating quiz content for lessons."""
    
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
        """Create the quiz generator agent with specific configuration."""
        return Agent(
            model=self.model,
            tools=self.tools,
            description="You are an expert AI quiz creator, specializing in generating educational quizzes for online course lessons.",
            instructions=[
                "Your task is to create a comprehensive quiz based on the provided lesson content, title, and course subject.",
                "The quiz should test the student's understanding of the key concepts covered in the lesson.",
                "Generate 3-5 multiple choice questions that are challenging but fair.",
                "Each question should have 4 answer options with only one correct answer.",
                "Questions should cover different aspects of the lesson content (concepts, applications, examples).",
                "Provide clear explanations for why the correct answer is right.",
                "Make sure questions are at an appropriate difficulty level for the course subject and difficulty.",
                "IMPORTANT: You MUST output your response exclusively in valid JSON format following the react-quiz-component schema.",
                "Do not include any other text or explanations before or after the JSON object.",
                "The quiz should be engaging and educational, helping students reinforce their learning.",
                "Use varied question types: conceptual understanding, practical application, and factual recall.",
                "Ensure all questions are directly related to the lesson content provided.",
                "Make incorrect answers plausible but clearly wrong to someone who understood the lesson.",
                "Keep question text clear and concise, avoiding ambiguity.",
                "Set appropriate point values: easier questions 10 points, harder questions 20 points."
            ],
            expected_output=(
                '{'
                '  "quizTitle": "string (lesson title + Quiz)",'
                '  "quizSynopsis": "string (brief description of what the quiz covers)",'
                '  "progressBarColor": "#9de1f6",'
                '  "nrOfQuestions": "string (number of questions)",'
                '  "questions": ['
                '    {'
                '      "question": "string (the question text)",'
                '      "questionType": "text",'
                '      "answerSelectionType": "single",'
                '      "answers": ["option1", "option2", "option3", "option4"],'
                '      "correctAnswer": "string (1, 2, 3, or 4)",'
                '      "messageForCorrectAnswer": "Correct answer. Good job.",'
                '      "messageForIncorrectAnswer": "Incorrect answer. Please try again.",'
                '      "explanation": "string (explanation of why this is correct)",'
                '      "point": "string (10 or 20)"'
                '    }'
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
                max_retries=3,  # Override default for quiz generation
                base_delay=2.0,  # Slightly shorter delay for quiz generation
                backoff_factor=2.0,
                max_delay=20.0
            )
        except Exception as e:
            logger.error(f"Quiz generation failed after all retries: {e}")
            # Return a structured error response that the service can handle
            class ErrorResponse:
                def __init__(self, error_msg):
                    self.content = None
                    self.error = error_msg
            
            return ErrorResponse(str(e))
    
    def run(self, query: str):
        """Run the quiz generator agent with the given query."""
        logger.info(f"Starting quiz generation with retry logic")
        return self._run_agent_with_retry(query) 