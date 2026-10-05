export interface User {
  id: number;
  name: string;
  email: string;
  role: 'student' | 'librarian' | 'admin';
  student_id?: string;
  branch?: string;
  semester?: number;
  profile_image?: string;
  library_id?: number;
  created_at: string;
  updated_at?: string;
}

export interface Library {
  id: number;
  name: string;
  code: string;
  campus: string;
  address?: string;
  contact_email?: string;
  phone?: string;
  is_active: boolean;
  created_at: string;
}

export interface Book {
  borrow_count?: number;
  average_rating?: number | null;
  review_count?: number;
  library_name?: string | null;
  library_campus?: string | null;
  id: number;
  title: string;
  author: string;
  isbn?: string;
  category?: string;
  description?: string;
  cover_image?: string;
  publication_year?: number;
  rack?: string;
  shelf?: string;
  library_id?: number;
  total_copies: number;
  available_copies: number;
  created_at: string;
}

export interface DigitalResource {
  distribution_basis?: string | null;
  rights_evidence?: string | null;
  reviewed_by?: number | null;
  reviewed_at?: string | null;
  archived_at?: string | null;
  id: number;
  title: string;
  author: string;
  description?: string;
  isbn?: string;
  resource_type: 'open_access' | 'uploaded_pdf' | 'external_link';
  access_type: 'free' | 'library_members' | 'external';
  provider: string;
  library_id?: number;
  uploaded_by?: number;
  file_url?: string;
  external_url?: string;
  cover_image?: string;
  subject?: string;
  category?: string;
  language?: string;
  publication_year?: number;
  license_name?: string;
  license_url?: string;
  is_published: boolean;
  download_allowed: boolean;
  created_at: string;
}

export interface Note {
  id: number;
  user_id: number;
  library_id?: number;
  title: string;
  description?: string;
  content?: string;
  subject?: string;
  semester?: number;
  branch?: string;
  file_url?: string;
  file_type?: string;
  file_size?: string;
  access_level?: string;
  status?: string;
  download_count: number;
  created_at: string;
}

export interface QuestionBank {
  id: number;
  title: string;
  description?: string;
  subject: string;
  semester: number;
  branch: string;
  exam_type: string;
  academic_year: string;
  file_url?: string;
  file_type?: string;
  total_questions: number;
  library_id?: number;
  download_count: number;
  created_at: string;
}

export interface BorrowRecord {
  id: number;
  user_id: number;
  book_id: number;
  borrowed_at: string;
  due_date: string;
  returned_at?: string;
  status: string;
  user?: User;
  book?: Book;
}

export interface Review {
  id: number;
  user_id: number;
  book_id: number;
  rating: number;
  comment?: string;
  created_at: string;
  user?: User;
}

export interface Reservation {
  id: number;
  user_id: number;
  book_id: number;
  queue_position: number;
  status: string;
  created_at: string;
  book?: Book;
}

export interface Notification {
  id: number;
  user_id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
}

export interface DashboardSummary {
  reader_level: number;
  xp: number;
  xp_required: number;
  reading_streak: number;
  books_read: number;
  badges_unlocked: number;
  missions: Mission[];
  recent_activity: Activity[];
}

export interface Mission {
  id: string;
  title: string;
  xp: number;
  completed: boolean;
}

export interface Activity {
  id: number;
  type: string;
  description: string;
  time_ago: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

// Runtime placeholder exports so non-type imports never fail in browser
export const User = {} as any;
export const Library = {} as any;
export const Book = {} as any;
export const DigitalResource = {} as any;
export const Note = {} as any;
export const QuestionBank = {} as any;
export const BorrowRecord = {} as any;
export const Review = {} as any;
export const Reservation = {} as any;
export const Notification = {} as any;
export const DashboardSummary = {} as any;
export const Mission = {} as any;
export const Activity = {} as any;
export const LoginResponse = {} as any;
