import axios from "axios";

export const ALLOWED_TYPES: Record<string, string> = {
  "application/pdf": ".pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "image/png": ".png",
  "image/jpeg": ".jpg / .jpeg",
  "image/webp": ".webp",
};

export const MAX_BYTES = 52_428_800; // 50 MB

export async function uploadToS3(presignedUrl: string, file: File): Promise<void> {
  await axios.put(presignedUrl, file, {
    headers: { "Content-Type": file.type },
  });
}
