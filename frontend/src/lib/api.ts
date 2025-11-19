import { config } from "@/lib/config";

export class ApiError extends Error {
  statusCode: number;

  details?: unknown;

  constructor(statusCode: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

export interface ApiRequestOptions extends RequestInit {
  token?: string | null;
  // When sending JSON payloads we default the content type. Allow overriding explicitly.
  headers?: HeadersInit;
}

function buildHeaders(token?: string | null, headers: HeadersInit = {}): HeadersInit {
  const merged = new Headers(headers);

  if (!merged.has("Content-Type")) {
    merged.set("Content-Type", "application/json");
  }

  if (token) {
    merged.set("Authorization", `Bearer ${token}`);
  }

  return merged;
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const text = await response.text();

  if (!text) {
    return undefined as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, "Failed to parse server response.");
  }
}

export async function apiRequest<T>(
  endpoint: string,
  { token, headers, ...options }: ApiRequestOptions = {},
): Promise<T> {
  const url = `${config.api.baseUrl}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: buildHeaders(token, headers),
    });

    if (response.status === 401) {
      // Force logout / redirect. Let ProtectedLayout handle redirect.
      // Only redirect if we're not already on the login page to avoid loops
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.replace("/login");
      }
      throw new ApiError(401, "Unauthorized");
    }

    if (response.status === 204) {
      return undefined as T;
    }

    if (!response.ok) {
      const errorBody = await response
        .json()
        .catch(() => ({ detail: "Request failed." }));

      const message =
        typeof errorBody?.detail === "string"
          ? errorBody.detail
          : "Request failed.";

      throw new ApiError(response.status, message, errorBody);
    }

    return parseJsonResponse<T>(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(0, "Network error. Please check your connection.");
  }
}

