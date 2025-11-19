import { ApiError } from "@/lib/api";

export type ExportFormat = "pdf" | "json";

export function mapExportError(error: unknown, format: ExportFormat): string {
  const fallback =
    format === "pdf"
      ? "Failed to export PDF. Please try again."
      : "Failed to export JSON. Please try again.";

  if (error instanceof ApiError) {
    if (error.statusCode === 401) {
      return "Session expired. Please sign in again.";
    }

    if (error.statusCode === 404) {
      return "Analysis not found. Please refresh and try again.";
    }

    if (error.statusCode === 0) {
      return "Network error. Please check your connection.";
    }

    return error.message || fallback;
  }

  if (error instanceof Error) {
    return error.message || fallback;
  }

  return fallback;
}

