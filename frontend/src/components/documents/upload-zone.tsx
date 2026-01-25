"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, XCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUploadDocument } from "@/hooks/use-documents";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ExtractionMethod, OCRMode } from "@/lib/api/types";

/**
 * Drag-and-drop file upload component with extraction method and OCR selection.
 *
 * Accepts PDF, DOCX, PNG, and JPG files (max 1 file at a time).
 * Shows loading state during upload and success/error feedback.
 */
export function UploadZone() {
  const { mutate, isPending, isSuccess, error, data, reset } =
    useUploadDocument();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [method, setMethod] = useState<ExtractionMethod>("docling");
  const [ocr, setOcr] = useState<OCRMode>("auto");

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        setSuccessMessage(null);
        mutate(
          { file: acceptedFiles[0], method, ocr },
          {
            onSuccess: (response) => {
              setSuccessMessage(
                `Uploaded: ${response.filename} (ID: ${response.id.slice(0, 8)}...)`
              );
            },
          }
        );
      }
    },
    [mutate, method, ocr]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
    maxFiles: 1,
    disabled: isPending,
  });

  const handleReset = () => {
    reset();
    setSuccessMessage(null);
  };

  return (
    <div className="space-y-4">
      {/* Extraction Options */}
      <div className="flex flex-wrap gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-muted-foreground">
            Extraction Method
          </label>
          <Select
            value={method}
            onValueChange={(value) => setMethod(value as ExtractionMethod)}
            disabled={isPending}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select method" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="docling">Docling (Fast)</SelectItem>
              <SelectItem value="langextract">LangExtract (Precise)</SelectItem>
              <SelectItem value="auto">Auto</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-muted-foreground">
            OCR Mode
          </label>
          <Select
            value={ocr}
            onValueChange={(value) => setOcr(value as OCRMode)}
            disabled={isPending}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Select OCR" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto Detect</SelectItem>
              <SelectItem value="force">Force OCR</SelectItem>
              <SelectItem value="skip">Skip OCR</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Method Description */}
      <div className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/50 rounded-md p-2">
        <Info className="h-4 w-4 mt-0.5 shrink-0" />
        <span>
          {method === "docling" && "Fast extraction for standard documents."}
          {method === "langextract" &&
            "Precise extraction with character-level source tracing."}
          {method === "auto" && "System selects best method based on document."}
        </span>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          "hover:border-primary/50 hover:bg-muted/50",
          isDragActive && "border-primary bg-primary/5",
          isPending && "opacity-50 cursor-not-allowed",
          error && "border-destructive"
        )}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          {isPending ? (
            <>
              <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
              <p className="text-muted-foreground">Uploading...</p>
            </>
          ) : isDragActive ? (
            <>
              <Upload className="h-8 w-8 text-primary" />
              <p className="text-primary font-medium">Drop the file here...</p>
            </>
          ) : (
            <>
              <Upload className="h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground">
                Drag and drop a file here, or click to select
              </p>
              <p className="text-xs text-muted-foreground">
                Accepts PDF, DOCX, PNG, JPG
              </p>
            </>
          )}
        </div>
      </div>

      {/* Success message */}
      {successMessage && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <CheckCircle className="h-4 w-4" />
          <span>{successMessage}</span>
          <button
            onClick={handleReset}
            className="ml-auto text-muted-foreground hover:text-foreground underline text-xs"
          >
            Upload another
          </button>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <XCircle className="h-4 w-4" />
          <span>{error.message}</span>
          <button
            onClick={handleReset}
            className="ml-auto text-muted-foreground hover:text-foreground underline text-xs"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
