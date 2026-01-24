"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUploadDocument } from "@/hooks/use-documents";

/**
 * Drag-and-drop file upload component for documents.
 *
 * Accepts PDF, DOCX, PNG, and JPG files (max 1 file at a time).
 * Shows loading state during upload and success/error feedback.
 */
export function UploadZone() {
  const { mutate, isPending, isSuccess, error, data, reset } =
    useUploadDocument();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        setSuccessMessage(null);
        mutate(acceptedFiles[0], {
          onSuccess: (response) => {
            setSuccessMessage(
              `Uploaded: ${response.filename} (ID: ${response.id.slice(0, 8)}...)`
            );
          },
        });
      }
    },
    [mutate]
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
    <div className="space-y-3">
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
