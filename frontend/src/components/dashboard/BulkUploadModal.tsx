"use client";

import { Button } from "@/components/ui";
import { ChangeEvent, FormEvent, MouseEvent, useCallback, useEffect, useRef, useState } from "react";
import styles from "./BulkUploadModal.module.css";

export interface BulkUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (file: File) => void | Promise<void>;
  loading?: boolean;
  error?: string | null;
  result?: {
    success_count: number;
    error_count: number;
    errors: Array<{ index: number; error: string }>;
  } | null;
}

export function BulkUploadModal({ 
  isOpen, 
  onClose, 
  onUpload, 
  loading = false, 
  error,
  result 
}: BulkUploadModalProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Handle modal open/close behavior
  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes (in cleanup)
      return () => {
        setSelectedFile(null);
        setFileError(null);
      };
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.removeProperty("overflow");
      // Reset state when modal closes
      setSelectedFile(null);
      setFileError(null);
    };
  }, [isOpen, onClose]);

  const handleOverlayClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    },
    [onClose],
  );

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setFileError(null);
    
    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.endsWith(".json")) {
      setFileError("Please select a JSON file");
      setSelectedFile(null);
      return;
    }

    // Validate JSON
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const json = JSON.parse(text);
        
        if (!Array.isArray(json)) {
          setFileError("JSON must be an array of company objects");
          setSelectedFile(null);
          return;
        }
        
        if (json.length === 0) {
          setFileError("JSON array cannot be empty");
          setSelectedFile(null);
          return;
        }
        
        setSelectedFile(file);
      } catch {
        setFileError("Invalid JSON file");
        setSelectedFile(null);
      }
    };
    reader.readAsText(file);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.overlay} role="presentation" onClick={handleOverlayClick}>
      <div
        ref={modalRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="bulk-upload-modal-title"
      >
        <header className={styles.header}>
          <h2 id="bulk-upload-modal-title">Bulk Upload Companies</h2>
          <p>Upload a JSON file to create multiple companies for testing/demo purposes.</p>
        </header>
        
        <form className={styles.form} onSubmit={handleSubmit}>
          {(error || fileError) && (
            <div className={styles.error} role="alert">
              {error || fileError}
            </div>
          )}
          
          {result && (
            <div className={styles.result}>
              <p className={styles.resultSuccess}>
                Successfully created {result.success_count} companies
              </p>
              {result.error_count > 0 && (
                <div className={styles.resultErrors}>
                  <p className={styles.resultErrorTitle}>
                    {result.error_count} error(s) occurred:
                  </p>
                  <ul>
                    {result.errors.map((err, idx) => (
                      <li key={idx}>
                        Item {err.index + 1}: {err.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          
          <div className={styles.fileInputWrapper}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              disabled={loading}
              className={styles.fileInput}
              id="bulk-upload-file"
            />
            <label htmlFor="bulk-upload-file" className={styles.fileLabel}>
              {selectedFile ? selectedFile.name : "Choose JSON file"}
            </label>
          </div>
          
          <div className={styles.actions}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={loading}>
              {result ? "Close" : "Cancel"}
            </Button>
            {!result && (
              <Button
                type="submit"
                disabled={!selectedFile || loading}
                isLoading={loading}
                loadingText="Uploading..."
              >
                Upload
              </Button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default BulkUploadModal;

