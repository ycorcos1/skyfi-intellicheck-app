"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { Select, type SelectOption } from "@/components/ui/Select";
import { useAuth } from "@/contexts/AuthContext";
import {
  generateDocumentUploadUrl,
  persistDocumentMetadata,
  uploadDocumentToS3,
} from "@/lib/documents-api";
import styles from "./UploadDocumentModal.module.css";

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

const DOCUMENT_TYPE_OPTIONS: SelectOption[] = [
  { value: "proof_of_address", label: "Proof of address" },
  { value: "business_license", label: "Business license" },
  { value: "other", label: "Other" },
];

interface UploadDocumentModalProps {
  companyId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function UploadDocumentModal({ companyId, isOpen, onClose, onSuccess }: UploadDocumentModalProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);
  const { getAccessToken } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<string>("");
  const [description, setDescription] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const isCompanyAvailable = useMemo(() => Boolean(companyId?.trim()), [companyId]);

  const resetState = useCallback(() => {
    setSelectedFile(null);
    setDocumentType("");
    setDescription("");
    setDragActive(false);
    setFileError(null);
    setFormError(null);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [onClose, resetState]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focusableSelectors =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    const focusFirstElement = () => {
      const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(focusableSelectors);
      if (focusableElements && focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        handleClose();
        return;
      }

      if (event.key !== "Tab" || !modalRef.current) {
        return;
      }

      const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(focusableSelectors);
      if (focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        if (activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else if (activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    const focusTimer = window.requestAnimationFrame(focusFirstElement);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusTimer);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.removeProperty("overflow");
      previouslyFocusedElementRef.current?.focus({ preventScroll: true });
    };
  }, [handleClose, isOpen]);

  const validateFile = useCallback((file: File | null) => {
    if (!file) {
      setFileError("Please choose a file to upload.");
      return false;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setFileError("File exceeds the 10 MB size limit.");
      return false;
    }

    setFileError(null);
    return true;
  }, []);

  const assignFile = useCallback(
    (file: File | null) => {
      if (!file) {
        setSelectedFile(null);
        setFileError("Please choose a file to upload.");
        return;
      }

      if (!validateFile(file)) {
        setSelectedFile(null);
        return;
      }

      setSelectedFile(file);
      setFileError(null);
    },
    [validateFile],
  );

  const handleBrowseClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files && event.target.files[0] ? event.target.files[0] : null;
      assignFile(file);
    },
    [assignFile],
  );

  const handleDragEnter = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);

      const file = event.dataTransfer.files && event.dataTransfer.files[0] ? event.dataTransfer.files[0] : null;
      assignFile(file);
    },
    [assignFile],
  );

  const handleSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      if (!isCompanyAvailable) {
        setFormError("Company is not available. Please refresh the page and try again.");
        return;
      }

      if (!selectedFile) {
        setFileError("Please choose a file to upload.");
        return;
      }

      if (!validateFile(selectedFile)) {
        return;
      }

      setIsUploading(true);
      setFormError(null);

      try {
        const token = await getAccessToken();

        if (!token) {
          throw new Error("Authentication required. Please sign in again.");
        }

        const uploadUrlResponse = await generateDocumentUploadUrl(
          companyId,
          {
            filename: selectedFile.name,
            file_size: selectedFile.size,
            mime_type: selectedFile.type || "application/octet-stream",
          },
          token,
        );

        await uploadDocumentToS3(uploadUrlResponse.upload_url, selectedFile);

        await persistDocumentMetadata(
          companyId,
          {
            document_id: uploadUrlResponse.document_id,
            filename: selectedFile.name,
            file_size: selectedFile.size,
            mime_type: selectedFile.type || "application/octet-stream",
            document_type: documentType ? documentType : null,
            description: description.trim() ? description.trim() : null,
          },
          token,
        );

        resetState();
        onSuccess();
      } catch (error) {
        console.error("Failed to upload document", error);
        setFormError("Failed to upload document. Please try again.");
      } finally {
        setIsUploading(false);
      }
    },
    [
      companyId,
      description,
      documentType,
      getAccessToken,
      isCompanyAvailable,
      onSuccess,
      resetState,
      selectedFile,
      validateFile,
    ],
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={styles.overlay}
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-document-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          handleClose();
        }
      }}
    >
      <div
        ref={modalRef}
        className={styles.modal}
        onMouseDown={(event) => {
          event.stopPropagation();
        }}
      >
        <div className={styles.header}>
          <h2 id="upload-document-title" className={styles.title}>
            Upload document
          </h2>
          <button type="button" className={styles.closeButton} aria-label="Close" onClick={handleClose}>
            ×
          </button>
        </div>

        {!isCompanyAvailable ? (
          <div className={styles.disabledNotice}>
            Company information is not available. Close this dialog and refresh the page to try again.
          </div>
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <div
              className={`${styles.dropZone} ${dragActive ? styles.dropZoneActive : ""}`}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.csv,.txt,.zip,.xls,.xlsx"
                onChange={handleFileChange}
              />
              <label>Drag &amp; drop a file here</label>
              <p className={styles.helperText}>or</p>
              <Button type="button" variant="secondary" onClick={handleBrowseClick}>
                Browse files
              </Button>
              <p className={styles.helperText}>Maximum file size: 10 MB.</p>
              {selectedFile ? (
                <div className={styles.fileInfo}>
                  <strong>Selected file:</strong>
                  <span>{selectedFile.name}</span>
                  <span>{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                </div>
              ) : null}
              {fileError ? <p className={styles.error}>{fileError}</p> : null}
            </div>

            <Select
              id="upload-document-type"
              label="Document type (optional)"
              placeholder="Select document type"
              options={DOCUMENT_TYPE_OPTIONS}
              value={documentType}
              onChange={(event) => {
                setDocumentType(event.target.value);
              }}
            />

            <label htmlFor="upload-document-description">
              Description (optional)
              <textarea
                id="upload-document-description"
                className={styles.textarea}
                placeholder="Add context or notes for this document."
                value={description}
                onChange={(event) => {
                  setDescription(event.target.value);
                }}
                maxLength={1000}
              />
            </label>

            {formError ? <div className={styles.formError}>{formError}</div> : null}

            <div className={styles.footer}>
              <Button
                type="button"
                variant="secondary"
                className={styles.secondaryButton}
                onClick={handleClose}
                disabled={isUploading}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className={styles.primaryButton}
                isLoading={isUploading}
                loadingText="Uploading document"
              >
                Upload document
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default UploadDocumentModal;

