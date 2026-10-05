import { isAxiosError } from 'axios';
import type { Book, BorrowRecord, Reservation } from '../types';

export function libraryError(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) return fallback;
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map(item => typeof item?.msg === 'string' ? item.msg : '').filter(Boolean);
    if (messages.length) return messages.join(' ');
  }
  return error.response ? fallback : 'Unable to reach the library server. Please try again.';
}

// Preserve explicit offsets and the existing local-time interpretation of
// legacy offset-free timestamps (the local PostgreSQL instance uses IST).
export function libraryDate(value: string): Date {
  return new Date(value);
}

export function loanAction(book: Book, borrows: BorrowRecord[], reservations: Reservation[]) {
  if (borrows.some(item => item.book_id === book.id && item.status === 'borrowed')) {
    return { kind: 'staff' as const, label: 'Already borrowed', disabled: true };
  }
  const reservation = reservations.find(item => item.book_id === book.id && ['pending', 'ready'].includes(item.status));
  if (reservation?.status === 'ready') return { kind: 'staff' as const, label: 'Ready for pickup — visit library', disabled: true };
  if (reservation) return { kind: 'reserve' as const, label: 'Reserved', disabled: true };
  return book.available_copies > 0
    ? { kind: 'staff' as const, label: 'Visit library to borrow', disabled: true }
    : { kind: 'reserve' as const, label: 'Reserve', disabled: false };
}
