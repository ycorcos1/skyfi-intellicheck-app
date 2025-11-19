"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { Button } from "@/components/ui";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/contexts/AuthContext";
import { createNote, deleteNote, listNotes, updateNote } from "@/lib/notes-api";
import type { Note } from "@/types/note";
import { NoteCard } from "./NoteCard";
import styles from "./NotesTab.module.css";

const MAX_NOTE_LENGTH = 5000;

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

export function NotesTab() {
  const params = useParams<{ id: string }>();
  const companyIdParam = params?.id;
  const companyId = useMemo(
    () => (Array.isArray(companyIdParam) ? companyIdParam[0] : companyIdParam),
    [companyIdParam],
  );

  const { getAccessToken, user } = useAuth();

  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const loadNotes = useCallback(async () => {
    if (!companyId) {
      setError("Company not found.");
      setNotes([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const token = await getAccessToken();

      if (!token) {
        setError("Authentication required. Please sign in again.");
        setNotes([]);
        return;
      }

      const response = await listNotes(companyId, token);
      setNotes(response.items);
    } catch (err) {
      console.error("Failed to load notes", err);
      setError("Unable to load notes. Please try again.");
      setNotes([]);
    } finally {
      setIsLoading(false);
    }
  }, [companyId, getAccessToken]);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

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

  const handleCreateNote = useCallback(async () => {
    const trimmed = newNoteContent.trim();

    if (!companyId) {
      setFormError("Company not found. Please refresh and try again.");
      return;
    }

    if (!trimmed) {
      setFormError("Please enter note content before saving.");
      return;
    }

    if (trimmed.length > MAX_NOTE_LENGTH) {
      setFormError(`Notes are limited to ${MAX_NOTE_LENGTH} characters.`);
      return;
    }

    setIsSubmitting(true);
    setFormError(null);

    try {
      const token = await getAccessToken();

      if (!token) {
        throw new Error("Authentication required.");
      }

      const created = await createNote(
        companyId,
        {
          content: trimmed,
        },
        token,
      );

      setNotes((previous) => [created, ...previous]);
      setNewNoteContent("");
      setShowForm(false);
      setFeedback({
        type: "success",
        message: "Note added successfully.",
      });
    } catch (err) {
      console.error("Failed to create note", err);
      setFormError("Failed to create note. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }, [companyId, getAccessToken, newNoteContent]);

  const handleUpdateNote = useCallback(
    async (noteId: string, content: string) => {
      if (!companyId) {
        throw new Error("Company not found.");
      }

      const token = await getAccessToken();

      if (!token) {
        throw new Error("Authentication required.");
      }

      const updated = await updateNote(
        companyId,
        noteId,
        {
          content,
        },
        token,
      );

      setNotes((previous) => previous.map((note) => (note.id === updated.id ? updated : note)));
      setFeedback({
        type: "success",
        message: "Note updated successfully.",
      });
    },
    [companyId, getAccessToken],
  );

  const handleDeleteNote = useCallback(
    async (noteId: string) => {
      if (!companyId) {
        throw new Error("Company not found.");
      }

      const token = await getAccessToken();

      if (!token) {
        throw new Error("Authentication required.");
      }

      await deleteNote(companyId, noteId, token);
      setNotes((previous) => previous.filter((note) => note.id !== noteId));
      setFeedback({
        type: "success",
        message: "Note deleted.",
      });
    },
    [companyId, getAccessToken],
  );

  const currentUserId = user?.id ?? user?.email;

  if (isLoading) {
    return (
      <div className={styles.stateWrapper}>
        <LoadingSkeleton rows={5} columns={4} />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <h2 className={styles.title}>Internal notes</h2>
          <p className={styles.subtitle}>Track operator collaboration, call summaries, and decisions for this company.</p>
        </div>
        <Button
          className={styles.addButton}
          onClick={() => {
            setShowForm(true);
            setFormError(null);
          }}
          disabled={showForm}
        >
          Add note
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
            onClick={() => {
              void loadNotes();
            }}
          >
            Retry
          </Button>
        </div>
      ) : null}

      {!error && showForm ? (
        <div className={styles.form}>
          <label htmlFor="new-note-content">New note</label>
          <textarea
            id="new-note-content"
            className={styles.textarea}
            value={newNoteContent}
            onChange={(event) => {
              setNewNoteContent(event.target.value);
            }}
            maxLength={MAX_NOTE_LENGTH}
            rows={6}
          />
          <span className={styles.charCount}>
            {newNoteContent.length}/{MAX_NOTE_LENGTH}
          </span>
          {formError ? <p className={styles.errorMessage}>{formError}</p> : null}
          <div className={styles.formActions}>
            <Button
              type="button"
              variant="secondary"
              className={styles.cancelButton}
              onClick={() => {
                setShowForm(false);
                setNewNoteContent("");
                setFormError(null);
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className={styles.submitButton}
              onClick={() => {
                void handleCreateNote();
              }}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Saving…" : "Save note"}
            </Button>
          </div>
        </div>
      ) : null}

      {!error && notes.length === 0 && !showForm ? (
        <div className={styles.stateWrapper}>
          <p className={styles.stateMessage}>No notes have been added yet. Create the first note to capture context.</p>
        </div>
      ) : null}

      {!error && notes.length > 0 ? (
        <div className={styles.notesList}>
          {notes.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              currentUserId={currentUserId}
              onUpdate={handleUpdateNote}
              onDelete={handleDeleteNote}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default NotesTab;
