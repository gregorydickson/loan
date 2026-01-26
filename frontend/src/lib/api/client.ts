/**
 * Base API client for making typed requests to the backend.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Custom error class that preserves structured error details from the API.
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Generic API client for making typed requests.
 *
 * @param path - API endpoint path (e.g., "/api/documents/")
 * @param options - Fetch options (method, body, headers, etc.)
 * @returns Typed JSON response
 * @throws ApiError with detail object on non-ok response
 */
export async function apiClient<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorDetail: unknown;
    let errorMessage: string;

    try {
      const errorBody = await response.json();
      errorDetail = errorBody.detail;

      // Extract user-friendly message
      if (typeof errorBody.detail === "string") {
        errorMessage = errorBody.detail;
      } else if (errorBody.detail?.message) {
        errorMessage = errorBody.detail.message;
      } else {
        errorMessage = JSON.stringify(errorBody.detail);
      }
    } catch {
      errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      errorDetail = undefined;
    }

    throw new ApiError(errorMessage, response.status, errorDetail);
  }

  return response.json() as Promise<T>;
}
