/**
 * TypeScript types matching backend Pydantic models.
 */

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  file_hash: string;
  file_size_bytes: number;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  message: string;
}

export interface DocumentStatusResponse {
  id: string;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  file_hash: string;
  file_type: string;
  file_size_bytes: number;
  gcs_uri: string | null;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface BorrowerSummary {
  id: string;
  name: string;
  confidence_score: string; // Decimal from backend serialized as string
  created_at: string;
  income_count: number;
}

export interface BorrowerListResponse {
  borrowers: BorrowerSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncomeRecord {
  id: string;
  amount: string; // Decimal from backend serialized as string
  period: string;
  year: number;
  source_type: string;
  employer: string | null;
}

export interface AccountNumber {
  id: string;
  number: string;
  account_type: string;
}

export interface SourceReference {
  id: string;
  document_id: string;
  page_number: number;
  section: string | null;
  snippet: string;
}

export interface BorrowerDetailResponse {
  id: string;
  name: string;
  address_json: string | null;
  confidence_score: string;
  created_at: string;
  income_records: IncomeRecord[];
  account_numbers: AccountNumber[];
  source_references: SourceReference[];
}

export interface BorrowerSourcesResponse {
  borrower_id: string;
  borrower_name: string;
  sources: SourceReference[];
}

// Extraction method and OCR mode types for dual pipeline support
export type ExtractionMethod = "docling" | "langextract" | "auto";
export type OCRMode = "auto" | "force" | "skip";

export interface UploadParams {
  file: File;
  method?: ExtractionMethod;
  ocr?: OCRMode;
}
