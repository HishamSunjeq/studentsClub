import axios from "axios";
import { apiInstance } from "@/api/client";

export type UploadStatus = "pending" | "finalized" | "failed";

export interface PresignResponse {
  upload_id: string;
  presigned_url: string;
  s3_key: string;
}

export interface Upload {
  id: string;
  user_id: string;
  subject_id: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  s3_key: string;
  status: UploadStatus;
  finalized_at: string | null;
  created_at: string;
}

export const ALLOWED_TYPES: Record<string, string> = {
  "application/pdf": ".pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "image/png": ".png",
  "image/jpeg": ".jpg / .jpeg",
  "image/webp": ".webp",
};

export const MAX_BYTES = 52_428_800; // 50 MB

export async function createUpload(payload: {
  filename: string;
  content_type: string;
  size_bytes: number;
  subject_id?: string;
}): Promise<PresignResponse> {
  const { data } = await apiInstance.post<PresignResponse>("/api/v1/uploads", payload);
  return data;
}

export async function uploadToS3(presignedUrl: string, file: File): Promise<void> {
  await axios.put(presignedUrl, file, {
    headers: { "Content-Type": file.type },
  });
}

export async function finalizeUpload(uploadId: string): Promise<Upload> {
  const { data } = await apiInstance.post<Upload>(`/api/v1/uploads/${uploadId}/finalize`);
  return data;
}

export async function getUpload(uploadId: string): Promise<Upload> {
  const { data } = await apiInstance.get<Upload>(`/api/v1/uploads/${uploadId}`);
  return data;
}
