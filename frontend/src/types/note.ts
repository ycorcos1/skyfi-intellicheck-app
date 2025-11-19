export interface Note {
  id: string;
  company_id: string;
  user_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface NoteListResponse {
  items: Note[];
  total: number;
}

export interface NoteCreateRequest {
  content: string;
}

export interface NoteUpdateRequest {
  content: string;
}

