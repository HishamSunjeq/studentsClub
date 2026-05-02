import { apiInstance } from "@/api/client";

export type QuizSessionStatus = "in_progress" | "completed" | "abandoned";
export type QuizDifficulty = "easy" | "medium" | "hard";

export interface QuizChoice {
  id: string;
  text: string;
  position: number;
}

export interface QuizQuestion {
  id: string;
  text: string;
  difficulty: QuizDifficulty;
  position: number;
  choices: QuizChoice[];
}

export interface QuizSession {
  id: string;
  user_id: string;
  subject_id: string;
  status: QuizSessionStatus;
  total_questions: number;
  score: number;
  completed_at: string | null;
  created_at: string;
}

export interface QuizSessionWithQuestions extends QuizSession {
  questions: QuizQuestion[];
  answered_question_ids?: string[];
}

export interface QuizAnswerResponse {
  is_correct: boolean;
  correct_choice_id: string;
  explanation: string | null;
  answered_count: number;
  score: number;
}

export async function fetchQuizSession(
  sessionId: string,
): Promise<QuizSessionWithQuestions> {
  const { data } = await apiInstance.get<QuizSessionWithQuestions>(
    `/api/v1/quizzes/${sessionId}/questions`,
  );
  return data;
}

export async function startQuiz(payload: {
  subject_id: string;
  count: number;
}): Promise<QuizSessionWithQuestions> {
  const { data } = await apiInstance.post<QuizSessionWithQuestions>(
    "/api/v1/quizzes",
    payload,
  );
  return data;
}

export async function submitAnswer(
  sessionId: string,
  payload: { question_id: string; choice_id: string },
): Promise<QuizAnswerResponse> {
  const { data } = await apiInstance.post<QuizAnswerResponse>(
    `/api/v1/quizzes/${sessionId}/answer`,
    payload,
  );
  return data;
}

export async function completeQuiz(sessionId: string): Promise<QuizSession> {
  const { data } = await apiInstance.post<QuizSession>(
    `/api/v1/quizzes/${sessionId}/complete`,
  );
  return data;
}
