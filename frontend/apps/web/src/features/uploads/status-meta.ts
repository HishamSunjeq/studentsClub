import {
  CheckCircle2,
  CircleDashed,
  CloudUpload,
  Loader2,
  Sparkles,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { UploadStatus } from "@/api/generated/schemas";
import type { QuestionSetStatus } from "@/api/generated/schemas";

type ChipVariant =
  | "neutral"
  | "primary"
  | "success"
  | "warning"
  | "destructive"
  | "outline";

export const UPLOAD_STATUS_META: Record<
  UploadStatus,
  {
    label: string;
    Icon: LucideIcon;
    variant: ChipVariant;
    spin?: boolean;
  }
> = {
  pending: { label: "Awaiting upload", Icon: CircleDashed, variant: "outline" },
  uploaded: { label: "Uploaded", Icon: CloudUpload, variant: "neutral" },
  extracting: {
    label: "Extracting text",
    Icon: Loader2,
    variant: "primary",
    spin: true,
  },
  ready: { label: "Ready", Icon: CheckCircle2, variant: "success" },
  failed: { label: "Failed", Icon: XCircle, variant: "destructive" },
};

export const QS_STATUS_META: Record<
  QuestionSetStatus,
  {
    label: string;
    Icon: LucideIcon;
    variant: ChipVariant;
    spin?: boolean;
  }
> = {
  generating: {
    label: "Generating",
    Icon: Sparkles,
    variant: "primary",
    spin: false,
  },
  generation_failed: {
    label: "Generation failed",
    Icon: XCircle,
    variant: "destructive",
  },
  draft: { label: "Draft", Icon: CircleDashed, variant: "outline" },
  published: { label: "Published", Icon: CheckCircle2, variant: "success" },
  rejected: { label: "Rejected", Icon: XCircle, variant: "neutral" },
};

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
