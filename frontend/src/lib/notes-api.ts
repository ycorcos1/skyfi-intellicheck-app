import { apiRequest } from "@/lib/api";
import type { Note, NoteListResponse, NoteCreateRequest, NoteUpdateRequest } from "@/types/note";

export async function listNotes(companyId: string, token: string | null) {
  return apiRequest<NoteListResponse>(`/v1/companies/${companyId}/notes`, {
    token,
  });
}

export async function createNote(companyId: string, payload: NoteCreateRequest, token: string | null) {
  return apiRequest<Note>(`/v1/companies/${companyId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export async function updateNote(
  companyId: string,
  noteId: string,
  payload: NoteUpdateRequest,
  token: string | null,
) {
  return apiRequest<Note>(`/v1/companies/${companyId}/notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    token,
  });
}

export async function deleteNote(companyId: string, noteId: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${companyId}/notes/${noteId}`, {
    method: "DELETE",
    token,
  });
}

