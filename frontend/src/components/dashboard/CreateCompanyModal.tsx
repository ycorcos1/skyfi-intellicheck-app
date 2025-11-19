"use client";

import { Button, Input } from "@/components/ui";
import { ChangeEvent, FormEvent, MouseEvent, useCallback, useEffect, useMemo, useState } from "react";
import styles from "./CreateCompanyModal.module.css";
import { useRef } from "react";

export interface CreateCompanyFormState {
  name: string;
  domain: string;
  website_url: string;
  email: string;
  phone: string;
}

export interface CreateCompanyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateCompanyFormState) => void | Promise<void>;
  loading?: boolean;
  error?: string | null;
}

const INITIAL_FORM_STATE: CreateCompanyFormState = {
  name: "",
  domain: "",
  website_url: "",
  email: "",
  phone: "",
};

export function CreateCompanyModal({ isOpen, onClose, onSubmit, loading = false, error }: CreateCompanyModalProps) {
  const [formState, setFormState] = useState<CreateCompanyFormState>(INITIAL_FORM_STATE);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedElementRef = useRef<HTMLElement | null>(null);

  const isSubmitDisabled = useMemo(() => {
    return !formState.name.trim() || !formState.domain.trim() || !formState.email.trim();
  }, [formState.domain, formState.email, formState.name]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    if (!isOpen) {
      return undefined;
    }

    previouslyFocusedElementRef.current = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";

    const focusableSelectors =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    const handleFocusTrap = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleKeyDown(event);
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

    document.addEventListener("keydown", handleFocusTrap);

    const focusTimer = window.requestAnimationFrame(() => {
      const nameInput = document.getElementById("create-company-name") as HTMLInputElement | null;
      nameInput?.focus();
    });

    return () => {
      document.removeEventListener("keydown", handleFocusTrap);
      document.body.style.removeProperty("overflow");
      window.cancelAnimationFrame(focusTimer);
      previouslyFocusedElementRef.current?.focus({ preventScroll: true });
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

  const handleChange = useCallback((field: keyof CreateCompanyFormState) => {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;
      setFormState((prev) => ({
        ...prev,
        [field]: value,
      }));
    };
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(formState);
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
        aria-labelledby="create-company-modal-title"
        aria-describedby="create-company-modal-description"
      >
        <header className={styles.header}>
          <h2 id="create-company-modal-title">Create Company</h2>
          <p id="create-company-modal-description">Add company information to begin verification.</p>
        </header>
        <form className={styles.form} onSubmit={handleSubmit}>
          {error ? (
            <div className={styles.error} role="alert">
              {error}
            </div>
          ) : null}
          <div className={styles.formGrid}>
            <Input
              id="create-company-name"
              label="Company Name"
              placeholder="NovaGeo Analytics"
              value={formState.name}
              onChange={handleChange("name")}
              required
            />
            <Input
              id="create-company-domain"
              label="Domain"
              placeholder="novageo.io"
              value={formState.domain}
              onChange={handleChange("domain")}
              required
            />
            <Input
              id="create-company-website"
              label="Website URL"
              placeholder="https://novageo.io"
              value={formState.website_url}
              onChange={handleChange("website_url")}
            />
            <Input
              id="create-company-email"
              type="email"
              label="Primary Email"
              placeholder="contact@novageo.io"
              value={formState.email}
              onChange={handleChange("email")}
              required
            />
            <Input
              id="create-company-phone"
              type="tel"
              label="Phone Number"
              placeholder="+1 (555) 123-4567"
              value={formState.phone}
              onChange={handleChange("phone")}
            />
          </div>
          <div className={styles.actions}>
            <Button variant="secondary" type="button" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitDisabled}
              isLoading={loading}
              loadingText="Creating company"
            >
              Create Company
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateCompanyModal;

