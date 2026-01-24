/**
 * Base API client for making typed requests to the backend.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Generic API client for making typed requests.
 *
 * @param path - API endpoint path (e.g., "/api/documents/")
 * @param options - Fetch options (method, body, headers, etc.)
 * @returns Typed JSON response
 * @throws Error with detail message on non-ok response
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
    let errorDetail: string;
    try {
      const errorBody = await response.json();
      errorDetail =
        typeof errorBody.detail === "string"
          ? errorBody.detail
          : JSON.stringify(errorBody.detail);
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}
