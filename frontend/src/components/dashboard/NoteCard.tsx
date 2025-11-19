"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui";
import type { Note } from "@/types/note";
import styles from "./NoteCard.module.css";

const MAX_NOTE_LENGTH = 5000;

interface NoteCardProps {
  note: Note;
  currentUserId?: string;
  onUpdate: (noteId: string, content: string) => Promise<void>;
  onDelete: (noteId: string) => Promise<void>;
}

function formatTimestamp(value: string) {
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

export function NoteCard({ note, currentUserId, onUpdate, onDelete }: NoteCardProps) {
  const mountedRef = useRef(true);

  const [isEditing, setIsEditing] = useState(false);
  const [draftContent, setDraftContent] = useState(note.content);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isAuthor = useMemo(() => {
    if (!currentUserId) {
      return false;
    }

    return note.user_id === currentUserId;
  }, [currentUserId, note.user_id]);

  useEffect(() => {
    if (!isEditing) {
      setDraftContent(note.content);
    }
  }, [isEditing, note.content]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const handleEdit = useCallback(() => {
    setError(null);
    setIsEditing(true);
  }, []);

  const handleCancel = useCallback(() => {
    setError(null);
    setDraftContent(note.content);
    setIsEditing(false);
  }, [note.content]);

  const handleSave = useCallback(async () => {
    const trimmed = draftContent.trim();

    if (!trimmed) {
      setError("Note content cannot be empty.");
      return;
    }

    if (trimmed.length > MAX_NOTE_LENGTH) {
      setError(`Notes are limited to ${MAX_NOTE_LENGTH} characters.`);
      return;
    }

    if (trimmed === note.content.trim()) {
      setError("No changes detected. Update the content or cancel.");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await onUpdate(note.id, trimmed);
      setIsEditing(false);
    } catch (err) {
      console.error("Failed to update note", err);
      setError("Failed to update note. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }, [draftContent, note.content, note.id, onUpdate]);

  const handleDelete = useCallback(async () => {
    const confirmed = window.confirm("Delete this note? This action cannot be undone.");

    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await onDelete(note.id);
    } catch (err) {
      console.error("Failed to delete note", err);
      if (mountedRef.current) {
        setError("Failed to delete note. Please try again.");
        setIsDeleting(false);
      }
      return;
    }

    if (mountedRef.current) {
      setIsDeleting(false);
    }
  }, [note.id, onDelete]);

  return (
    <article className={styles.card}>
      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Author</span>
          <span>{note.user_id || "Unknown"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Created</span>
          <span>{formatTimestamp(note.created_at)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Updated</span>
          <span>{formatTimestamp(note.updated_at)}</span>
        </div>
      </div>

      {isEditing ? (
        <div className={styles.editor}>
          <textarea
            className={styles.textarea}
            value={draftContent}
            maxLength={MAX_NOTE_LENGTH}
            onChange={(event) => {
              setDraftContent(event.target.value);
            }}
            rows={6}
          />
          <span className={styles.charCount}>
            {draftContent.length}/{MAX_NOTE_LENGTH}
          </span>
          {error ? <p className={styles.error}>{error}</p> : null}
          <div className={styles.editorActions}>
            <Button
              type="button"
              variant="secondary"
              className={styles.secondaryButton}
              onClick={handleCancel}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button type="button" onClick={handleSave} disabled={isSaving}>
              {isSaving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <p className={styles.content}>{note.content}</p>
          {error ? <p className={styles.error}>{error}</p> : null}
          {isAuthor ? (
            <div className={styles.actions}>
              <Button type="button" variant="secondary" className={styles.secondaryButton} onClick={handleEdit}>
                Edit
              </Button>
              <Button
                type="button"
                className={styles.dangerButton}
                onClick={() => {
                  void handleDelete();
                }}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting…" : "Delete"}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </article>
  );
}

export default NoteCard;

