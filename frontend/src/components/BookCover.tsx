import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import api from '../services/api';
import type { Book } from '../types';

export default function BookCover({ book, className = '' }: { book: Pick<Book, 'title' | 'author' | 'cover_image'>; className?: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  let source: string | undefined;
  try {
    if (book.cover_image) {
      const url = new URL(book.cover_image, new URL(api.defaults.baseURL || '/', window.location.origin));
      if (['http:', 'https:'].includes(url.protocol)) source = url.href;
    }
  } catch { /* An invalid cover URL uses the title fallback. */ }
  return (
    <div className={`overflow-hidden rounded-card bg-elevated border border-line flex items-center justify-center ${className}`}>
      {source && source !== failedUrl ? (
        <img src={source} alt={`Cover of ${book.title}`} loading="lazy" className="w-full h-full object-contain" onError={() => setFailedUrl(source!)} />
      ) : (
        <div className="p-4 text-center min-w-0">
          <BookOpen aria-hidden="true" className="w-8 h-8 mx-auto text-blue-400 mb-3" />
          <p className="text-body font-semibold text-ink line-clamp-3">{book.title}</p>
          <p className="bb-meta mt-2 line-clamp-2">{book.author}</p>
        </div>
      )}
    </div>
  );
}
