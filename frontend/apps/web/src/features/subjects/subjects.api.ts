import { apiInstance } from "@/api/client";

export interface Subject {
  id: string;
  name: string;
  code: string;
  college: string;
  academic_year: number;
  description: string | null;
  created_at: string;
}

export interface SubjectPage {
  items: Subject[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export async function fetchSubjects(params: {
  college?: string;
  academic_year?: number;
  page?: number;
  size?: number;
}): Promise<SubjectPage> {
  const { data } = await apiInstance.get<SubjectPage>("/api/v1/subjects", { params });
  return data;
}

export async function fetchMySubjects(params?: {
  page?: number;
  size?: number;
}): Promise<SubjectPage> {
  const { data } = await apiInstance.get<SubjectPage>("/api/v1/subjects/me", { params });
  return data;
}

export async function enrollSubject(subjectId: string): Promise<void> {
  await apiInstance.post(`/api/v1/subjects/${subjectId}/enroll`);
}

export async function unenrollSubject(subjectId: string): Promise<void> {
  await apiInstance.delete(`/api/v1/subjects/${subjectId}/enroll`);
}
