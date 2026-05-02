import { apiInstance } from "@/api/client";

export type QuestionSetStatus = "draft" | "published" | "rejected";
export type QuestionDifficulty = "easy" | "medium" | "hard";

export interface QuestionChoice {
  id: string;
  text: string;
  is_correct: boolean;
  position: number;
}

export interface Question {
  id: string;
  question_set_id: string;
  text: string;
  explanation: string | null;
  difficulty: QuestionDifficulty;
  source_excerpt: string | null;
  is_active: boolean;
  position: number;
  choices: QuestionChoice[];
}

export interface QuestionSet {
  id: string;
  upload_id: string;
  subject_id: string | null;
  created_by: string;
  title: string;
  status: QuestionSetStatus;
  ai_model: string;
  tokens_used: number;
  created_at: string;
  updated_at: string;
}

export interface QuestionSetWithQuestions extends QuestionSet {
  questions: Question[];
}

export interface QuestionSetList {
  items: QuestionSet[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export async function fetchMyQuestionSets(params: {
  status?: QuestionSetStatus;
  page?: number;
  size?: number;
} = {}): Promise<QuestionSetList> {
  const { data } = await apiInstance.get<QuestionSetList>(
    "/api/v1/question-sets/me",
    { params },
  );
  return data;
}

export async function fetchQuestionSet(id: string): Promise<QuestionSetWithQuestions> {
  const { data } = await apiInstance.get<QuestionSetWithQuestions>(
    `/api/v1/question-sets/${id}`,
  );
  return data;
}

export async function publishQuestionSet(id: string): Promise<QuestionSet> {
  const { data } = await apiInstance.post<QuestionSet>(
    `/api/v1/question-sets/${id}/publish`,
  );
  return data;
}

export async function rejectQuestionSet(id: string): Promise<QuestionSet> {
  const { data } = await apiInstance.post<QuestionSet>(
    `/api/v1/question-sets/${id}/reject`,
  );
  return data;
}

export async function updateQuestion(
  questionId: string,
  payload: {
    text?: string;
    explanation?: string;
    difficulty?: QuestionDifficulty;
    choices?: Array<{ text: string; is_correct: boolean }>;
  },
): Promise<Question> {
  const { data } = await apiInstance.patch<Question>(
    `/api/v1/questions/${questionId}`,
    payload,
  );
  return data;
}

export async function deactivateQuestion(questionId: string): Promise<void> {
  await apiInstance.delete(`/api/v1/questions/${questionId}`);
}
