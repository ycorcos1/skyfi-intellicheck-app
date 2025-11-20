"use client";

import { Button } from "@/components/ui";
import { MouseEvent, useCallback, useEffect, useRef } from "react";
import styles from "./DeleteCompanyModal.module.css";
import { Company } from "@/types/company";

export interface DeleteCompanyModalProps {
  isOpen: boolean;
  company: Company | null;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  isLoading?: boolean;
}

export function DeleteCompanyModal({
  isOpen,
  company,
  onClose,
  onConfirm,
  isLoading = false,
}: DeleteCompanyModalProps) {
  const modalRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isLoading) {
        onClose();
      }
    };

    if (!isOpen) {
      return undefined;
    }

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    document.addEventListener("keydown", handleKeyDown);

    const focusTimer = window.requestAnimationFrame(() => {
      const cancelButton = modalRef.current?.querySelector(
        'button[type="button"]'
      ) as HTMLButtonElement | null;
      cancelButton?.focus();
    });

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.removeProperty("overflow");
      window.cancelAnimationFrame(focusTimer);
      previouslyFocusedElementRef.current?.focus({ preventScroll: true });
    };
  }, [isOpen, onClose, isLoading]);

  const handleOverlayClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget && !isLoading) {
        onClose();
      }
    },
    [onClose, isLoading],
  );

  const handleConfirm = useCallback(() => {
    void onConfirm();
  }, [onConfirm]);

  if (!isOpen || !company) {
    return null;
  }

  return (
    <div
      className={styles.overlay}
      role="presentation"
      onClick={handleOverlayClick}
    >
      <div
        ref={modalRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-company-modal-title"
        aria-describedby="delete-company-modal-description"
      >
        <header className={styles.header}>
          <h2 id="delete-company-modal-title">Delete Company</h2>
        </header>
        <div className={styles.content}>
          <p id="delete-company-modal-description">
            Permanently delete <strong>{company.name}</strong>? This action
            cannot be undone. All associated data (analyses, documents, notes)
            will be permanently deleted.
          </p>
        </div>
        <div className={styles.actions}>
          <Button
            variant="secondary"
            type="button"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            className={styles.dangerButton}
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            isLoading={isLoading}
            loadingText="Deleting..."
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

export default DeleteCompanyModal;

