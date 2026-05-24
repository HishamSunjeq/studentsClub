import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileText } from "lucide-react";
import {
  useAdminExtractionGet,
  useAdminExtractionUpdate,
  getAdminExtractionGetQueryKey,
} from "@/api/generated/endpoints/admin/admin";
import type { ExtractionSettingsUpdateRequest } from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STRATEGIES = ["auto", "hi_res", "ocr_only", "fast"] as const;
const COMMON_LANGS = [
  { code: "eng", label: "English" },
  { code: "ara", label: "Arabic" },
  { code: "fra", label: "French" },
  { code: "deu", label: "German" },
  { code: "spa", label: "Spanish" },
  { code: "tur", label: "Turkish" },
];

export default function ExtractionPage() {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useAdminExtractionGet();
  const update = useAdminExtractionUpdate();

  const [backend, setBackend] = useState("unstructured");
  const [strategy, setStrategy] = useState("auto");
  const [langs, setLangs] = useState<string[]>(["eng", "ara"]);
  const [extractTables, setExtractTables] = useState(true);
  const [hiResModel, setHiResModel] = useState("");
  const [maxChars, setMaxChars] = useState("");

  useEffect(() => {
    if (!data) return;
    setBackend(data.backend);
    setStrategy(data.strategy);
    setLangs(data.ocr_languages ?? []);
    setExtractTables(data.extract_tables);
    setHiResModel(data.hi_res_model_name ?? "");
    setMaxChars(data.max_characters != null ? String(data.max_characters) : "");
  }, [data]);

  const toggleLang = (code: string) =>
    setLangs((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );

  const save = () => {
    if (langs.length === 0) {
      toast.error("Select at least one OCR language");
      return;
    }
    const body: ExtractionSettingsUpdateRequest = {
      backend: backend as ExtractionSettingsUpdateRequest["backend"],
      strategy: strategy as ExtractionSettingsUpdateRequest["strategy"],
      ocr_languages: langs,
      extract_tables: extractTables,
      hi_res_model_name: hiResModel.trim() || null,
      max_characters: maxChars ? Number(maxChars) : null,
    };
    update.mutate(
      { data: body },
      {
        onSuccess: () => {
          toast.success("Extraction settings saved");
          queryClient.invalidateQueries({
            queryKey: getAdminExtractionGetQueryKey(),
          });
        },
        onError: () => toast.error("Save failed"),
      },
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-16 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        Could not load extraction settings.
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-start gap-3 rounded-xl border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
        <FileText className="mt-0.5 size-4 shrink-0" strokeWidth={1.5} />
        <p>
          Controls how uploaded documents become text. The{" "}
          <span className="font-medium text-foreground">unstructured</span>{" "}
          backend runs layout detection + OCR (tesseract) — it reads
          right-to-left scripts like Arabic correctly, unlike the legacy
          extractor. Changes apply to the next upload.
        </p>
      </div>

      <div className="space-y-1.5">
        <Label>Backend</Label>
        <Select value={backend} onValueChange={setBackend}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="unstructured">unstructured (recommended)</SelectItem>
            <SelectItem value="legacy">legacy (pdfplumber / tesseract)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label>Strategy</Label>
        <Select
          value={strategy}
          onValueChange={setStrategy}
          disabled={backend !== "unstructured"}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STRATEGIES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          <span className="font-medium">auto</span> picks per page;{" "}
          <span className="font-medium">hi_res</span> / ocr_only force OCR
          (best for scanned or Arabic docs); fast is text-only.
        </p>
      </div>

      <div className="space-y-2">
        <Label>OCR languages</Label>
        <div className="flex flex-wrap gap-3">
          {COMMON_LANGS.map((l) => (
            <label
              key={l.code}
              className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm"
            >
              <Checkbox
                checked={langs.includes(l.code)}
                onCheckedChange={() => toggleLang(l.code)}
                disabled={backend !== "unstructured"}
              />
              {l.label}{" "}
              <span className="text-xs text-muted-foreground">({l.code})</span>
            </label>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <Checkbox
          checked={extractTables}
          onCheckedChange={(v) => setExtractTables(v === true)}
          disabled={backend !== "unstructured"}
        />
        Extract tables (infer table structure as HTML)
      </label>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="hires">hi_res model (optional)</Label>
          <Input
            id="hires"
            value={hiResModel}
            onChange={(e) => setHiResModel(e.target.value)}
            placeholder="detectron2_onnx"
            disabled={backend !== "unstructured" || strategy !== "hi_res"}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="maxchars">Max characters (optional)</Label>
          <Input
            id="maxchars"
            type="number"
            value={maxChars}
            onChange={(e) => setMaxChars(e.target.value)}
            disabled={backend !== "unstructured"}
          />
        </div>
      </div>

      <Button onClick={save} disabled={update.isPending}>
        Save settings
      </Button>
    </div>
  );
}
