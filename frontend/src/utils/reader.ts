export interface ReaderBookmark { page: number; note: string }
export interface ReaderState { page: number; bookmarks: ReaderBookmark[] }
export const emptyReaderState = (): ReaderState => ({ page: 1, bookmarks: [] });
export const validReaderPage = (page: number) => Number.isSafeInteger(page) && page >= 1 && page <= 100000;
export const readerKey = (userId: number, resourceId: string) => `bookbridge:reader:v1:${userId}:${resourceId}`;

export function parseReaderState(raw: string | null): ReaderState {
  if (!raw) return emptyReaderState();
  const value = JSON.parse(raw);
  if (!value || !validReaderPage(value.page) || !Array.isArray(value.bookmarks)) throw new Error('Invalid saved reader data');
  const seen = new Set<number>();
  const bookmarks: ReaderBookmark[] = [];
  for (const item of value.bookmarks) {
    if (item && validReaderPage(item.page) && typeof item.note === 'string' && !seen.has(item.page)) {
      bookmarks.push({ page: item.page, note: item.note.slice(0, 2000) });
      seen.add(item.page);
    }
    if (bookmarks.length === 200) break;
  }
  return { page: value.page, bookmarks: bookmarks.sort((a, b) => a.page - b.page) };
}

export function readerUrl(raw: string | undefined, apiBase: string): string | null {
  if (!raw?.trim()) return null;
  try {
    const url = new URL(raw, apiBase.endsWith('/') ? apiBase : apiBase + '/');
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}
