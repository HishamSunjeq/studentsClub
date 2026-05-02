import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useAuthStore } from "@/features/auth/auth.store";
import { fetchMySubjects } from "@/features/subjects/subjects.api";
import {
  ALLOWED_TYPES,
  MAX_BYTES,
  createUpload,
  finalizeUpload,
  uploadToS3,
} from "@/features/uploads/uploads.api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type UploadStep = "idle" | "uploading" | "finalizing" | "done" | "error";

export default function UploadPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [file, setFile] = useState<File | null>(null);
  const [subjectId, setSubjectId] = useState("");
  const [step, setStep] = useState<UploadStep>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [uploadId, setUploadId] = useState("");
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: mySubjects } = useQuery({
    queryKey: ["subjects/me"],
    queryFn: () => fetchMySubjects({ size: 100 }),
    enabled: !!user,
  });

  if (!user) {
    navigate("/login");
    return null;
  }

  function pickFile(picked: File) {
    if (!ALLOWED_TYPES[picked.type]) {
      setErrorMsg(`File type not allowed. Accepted: ${Object.values(ALLOWED_TYPES).join(", ")}`);
      return;
    }
    if (picked.size > MAX_BYTES) {
      setErrorMsg(`File exceeds the 50 MB limit.`);
      return;
    }
    setErrorMsg("");
    setFile(picked);
    setStep("idle");
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    if (picked) pickFile(picked);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const picked = e.dataTransfer.files?.[0];
    if (picked) pickFile(picked);
  }

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("No file selected");
      setStep("uploading");
      setProgress(0);

      const presign = await createUpload({
        filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
        subject_id: subjectId || undefined,
      });

      setProgress(30);
      await uploadToS3(presign.presigned_url, file);
      setProgress(80);
      setStep("finalizing");

      const result = await finalizeUpload(presign.upload_id);
      setProgress(100);
      setStep("done");
      setUploadId(result.id);
    },
    onError: (err: Error) => {
      setStep("error");
      setErrorMsg(err.message || "Upload failed. Please try again.");
    },
  });

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Upload Study Material</CardTitle>
          <CardDescription>
            Supported: PDF, DOCX, PNG, JPEG, WEBP · Max 50 MB
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">

          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
            }`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept={Object.keys(ALLOWED_TYPES).join(",")}
              onChange={onFileChange}
            />
            {file ? (
              <div>
                <p className="font-medium text-sm">{file.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Drop a file here or <span className="text-primary underline">browse</span>
              </p>
            )}
          </div>

          {/* Subject selector */}
          {mySubjects && mySubjects.items.length > 0 && (
            <div className="space-y-1">
              <label className="text-sm font-medium">Subject (optional)</label>
              <select
                className="w-full h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
              >
                <option value="">— select subject —</option>
                {mySubjects.items.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Progress */}
          {step !== "idle" && step !== "error" && (
            <div className="space-y-1">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground text-center">
                {step === "uploading" && "Uploading to storage…"}
                {step === "finalizing" && "Finalising…"}
                {step === "done" && "Done!"}
              </p>
            </div>
          )}

          {/* Error */}
          {errorMsg && (
            <p className="text-sm text-destructive">{errorMsg}</p>
          )}

          {/* Done state */}
          {step === "done" ? (
            <div className="flex gap-2">
              <Button
                className="flex-1"
                onClick={() => {
                  setFile(null);
                  setStep("idle");
                  setProgress(0);
                  setUploadId("");
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                variant="outline"
              >
                Upload another
              </Button>
              <Button className="flex-1" onClick={() => navigate("/subjects")}>
                Browse subjects
              </Button>
            </div>
          ) : (
            <Button
              className="w-full"
              disabled={!file || step === "uploading" || step === "finalizing"}
              onClick={() => uploadMutation.mutate()}
            >
              {step === "uploading" || step === "finalizing" ? "Uploading…" : "Upload"}
            </Button>
          )}

          <Button variant="ghost" className="w-full" onClick={() => navigate("/")}>
            ← Back
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
