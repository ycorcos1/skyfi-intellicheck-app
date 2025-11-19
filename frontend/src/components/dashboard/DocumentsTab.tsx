"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/contexts/AuthContext";
import {
  deleteDocument,
  generateDocumentDownloadUrl,
  listDocuments,
} from "@/lib/documents-api";
import type { Document } from "@/types/document";
import { UploadDocumentModal } from "./UploadDocumentModal";
import styles from "./DocumentsTab.module.css";

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  proof_of_address: "Proof of address",
  business_license: "Business license",
  other: "Other",
};

function formatFileSize(bytes: number) {
  if (Number.isNaN(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** index;

  if (index === 0) {
    return `${bytes} B`;
  }

  return `${size.toFixed(index === 1 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string) {
  if (!value) {
    return "Unknown";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface DocumentCardProps {
  document: Document;
  onDownload: (document: Document) => Promise<void>;
  onDelete: (document: Document) => Promise<void>;
  isDownloading: boolean;
  isDeleting: boolean;
}

function DocumentCard({ document: documentItem, onDownload, onDelete, isDownloading, isDeleting }: DocumentCardProps) {
  const documentTypeLabel =
    (documentItem.document_type && DOCUMENT_TYPE_LABELS[documentItem.document_type]) || "Uncategorized";

  return (
    <article className={styles.documentCard}>
      <header className={styles.documentHeader}>
        <div>
          <h3 className={styles.documentTitle}>{documentItem.filename}</h3>
          <span className={styles.documentBadge}>{documentTypeLabel}</span>
        </div>
      </header>

      <div className={styles.metaGrid}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Uploaded</span>
          <span className={styles.metaValue}>{formatDate(documentItem.created_at)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Uploaded By</span>
          <span className={styles.metaValue}>{documentItem.uploaded_by || "Unknown"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>File Size</span>
          <span className={styles.metaValue}>{formatFileSize(documentItem.file_size)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>MIME Type</span>
          <span className={styles.metaValue}>{documentItem.mime_type}</span>
        </div>
      </div>

      {documentItem.description ? (
        <p className={styles.documentDescription}>{documentItem.description}</p>
      ) : null}

      <div className={styles.documentActions}>
        <Button
          variant="secondary"
          className={styles.secondaryButton}
          onClick={() => {
            void onDownload(documentItem);
          }}
          isLoading={isDownloading}
          loadingText="Preparing download"
        >
          Download
        </Button>
        <Button
          className={styles.dangerButton}
          onClick={() => {
            void onDelete(documentItem);
          }}
          isLoading={isDeleting}
          loadingText="Deleting document"
        >
          Delete
        </Button>
      </div>
    </article>
  );
}

export function DocumentsTab() {
  const params = useParams<{ id: string }>();
  const companyIdParam = params?.id;
  const companyId = useMemo(
    () => (Array.isArray(companyIdParam) ? companyIdParam[0] : companyIdParam),
    [companyIdParam],
  );

  const { getAccessToken } = useAuth();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!companyId) {
      setError("Company not found.");
      setDocuments([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const token = await getAccessToken();

      if (!token) {
        setError("Authentication required. Please sign in again.");
        setDocuments([]);
        return;
      }

      const response = await listDocuments(companyId, token);
      setDocuments(response.items);
    } catch (err) {
      console.error("Failed to load documents", err);
      setError("Unable to load documents. Please try again.");
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, getAccessToken]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!feedback) {
      return;
    }

    const timer = window.setTimeout(() => {
      setFeedback(null);
    }, 5000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [feedback]);

  const handleDownload = useCallback(
    async (documentItem: Document) => {
      try {
        if (!companyId) {
          throw new Error("Company not found.");
        }

        setDownloadingId(documentItem.id);

        const token = await getAccessToken();

        if (!token) {
          throw new Error("Authentication required. Please sign in again.");
        }

        const response = await generateDocumentDownloadUrl(companyId, documentItem.id, token);

        const link = window.document.createElement("a");
        link.href = response.download_url;
        link.download = response.filename ?? documentItem.filename;
        link.rel = "noopener";
        window.document.body.appendChild(link);
        link.click();
        link.remove();

        setFeedback({
          type: "success",
          message: `Started download for ${documentItem.filename}.`,
        });
      } catch (err) {
        console.error("Failed to download document", err);
        setFeedback({
          type: "error",
          message: "Failed to prepare download. Please try again.",
        });
      } finally {
        setDownloadingId(null);
      }
    },
    [companyId, getAccessToken],
  );

  const handleDelete = useCallback(
    async (documentItem: Document) => {
      const confirmation = window.confirm(
        `Delete ${documentItem.filename}? This will remove the document permanently.`,
      );

      if (!confirmation) {
        return;
      }

      try {
        if (!companyId) {
          throw new Error("Company not found.");
        }

        setDeletingId(documentItem.id);

        const token = await getAccessToken();

        if (!token) {
          throw new Error("Authentication required. Please sign in again.");
        }

        await deleteDocument(companyId, documentItem.id, token);
        await loadDocuments();

        setFeedback({
          type: "success",
          message: `${documentItem.filename} was deleted.`,
        });
      } catch (err) {
        console.error("Failed to delete document", err);
        setFeedback({
          type: "error",
          message: "Failed to delete document. Please try again.",
        });
      } finally {
        setDeletingId(null);
      }
    },
    [companyId, getAccessToken, loadDocuments],
  );

  const handleUploadSuccess = useCallback(() => {
    setIsUploadModalOpen(false);
    setFeedback({
      type: "success",
      message: "Document uploaded successfully.",
    });
    void loadDocuments();
  }, [loadDocuments]);

  if (isLoading) {
    return (
      <div className={styles.stateWrapper}>
        <LoadingSkeleton rows={4} columns={3} />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <h2 className={styles.title}>Documents</h2>
          <p className={styles.subtitle}>
            Upload supporting documents, download existing files, and keep company records up to date.
          </p>
        </div>
        <Button
          className={styles.uploadButton}
          onClick={() => {
            setIsUploadModalOpen(true);
          }}
        >
          Upload document
        </Button>
      </div>

      {feedback ? (
        <div
          className={`${styles.feedback} ${
            feedback.type === "success" ? styles.feedbackSuccess : styles.feedbackError
          }`}
        >
          <span>{feedback.message}</span>
          <button
            type="button"
            className={styles.feedbackClose}
            onClick={() => {
              setFeedback(null);
            }}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      ) : null}

      {error ? (
        <div className={styles.stateWrapper}>
          <p className={`${styles.stateMessage} ${styles.errorMessage}`}>{error}</p>
          <Button
            variant="secondary"
            className={styles.retryButton}
            onClick={() => {
              void loadDocuments();
            }}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {!error && documents.length === 0 ? (
        <div className={styles.stateWrapper}>
          <p className={styles.stateMessage}>No documents have been uploaded yet.</p>
          <Button
            onClick={() => {
              setIsUploadModalOpen(true);
            }}
          >
            Upload the first document
          </Button>
        </div>
      ) : null}

      {!error && documents.length > 0 ? (
        <div className={styles.documentList}>
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              onDownload={handleDownload}
              onDelete={handleDelete}
              isDownloading={downloadingId === doc.id}
              isDeleting={deletingId === doc.id}
            />
          ))}
        </div>
      ) : null}

      <UploadDocumentModal
        companyId={companyId ?? ""}
        isOpen={isUploadModalOpen}
        onClose={() => {
          setIsUploadModalOpen(false);
        }}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
}

export default DocumentsTab;
