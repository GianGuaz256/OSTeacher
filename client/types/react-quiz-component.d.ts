declare module 'react-quiz-component' {
  interface QuizQuestion {
    question: string;
    questionType: string;
    answerSelectionType: string;
    answers: string[];
    correctAnswer: string;
    messageForCorrectAnswer: string;
    messageForIncorrectAnswer: string;
    explanation?: string;
    point?: string;
  }

  interface QuizData {
    quizTitle: string;
    quizSynopsis: string;
    progressBarColor?: string;
    nrOfQuestions: string;
    questions: QuizQuestion[];
    showDefaultResult?: boolean;
    customResultPage?: (result: any) => JSX.Element;
    timer?: number;
    onComplete?: (result: any) => void;
  }

  interface QuizProps {
    quiz: QuizData;
    shuffle?: boolean;
    showInstantFeedback?: boolean;
    continueTillCorrect?: boolean;
    onComplete?: (result: any) => void;
  }

  const Quiz: React.ComponentType<QuizProps>;
  export default Quiz;
} 