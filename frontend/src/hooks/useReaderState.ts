import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { libraryError } from '../utils/library';
import type { ReaderBookmark } from '../utils/reader';

export interface HighlightRect { x: number; y: number; width: number; height: number }
export interface ReaderHighlight { id: string; page: number; text: string; note: string; rects: HighlightRect[] }
export interface SyncedReaderState {
  page: number; total_pages: number | null; document_key: string;
  bookmarks: ReaderBookmark[]; highlights: ReaderHighlight[]; theme: 'light' | 'sepia' | 'dark';
}
const empty = (): SyncedReaderState => ({ page: 1, total_pages: null, document_key: '', bookmarks: [], highlights: [], theme: 'light' });

export function useReaderState(resourceId: number) {
  const [data, setData] = useState<SyncedReaderState>(empty);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const latest = useRef(empty());
  const revision = useRef(0);
  const change = useRef(0);
  const saved = useRef(0);
  const busy = useRef(false);
  const alive = useRef(true);
  const blocked = useRef(false);

  useEffect(() => {
    let cancelled = false;
    alive.current = true;
    api.get(`/reader/${resourceId}/state`).then(({ data: response }) => {
      if (cancelled) return;
      const { version, ...value } = response;
      latest.current = value; revision.current = version;
      setData(value); setReady(true);
    }).catch(reason => { if (!cancelled) setError(libraryError(reason, 'Reading data could not be loaded. Reload to try again.')); });
    const warn = (event: BeforeUnloadEvent) => {
      if (change.current !== saved.current) { event.preventDefault(); event.returnValue = ''; }
    };
    window.addEventListener('beforeunload', warn);
    return () => { cancelled = true; alive.current = false; window.removeEventListener('beforeunload', warn); };
  }, [resourceId]);

  const flush = useCallback(async () => {
    if (busy.current || blocked.current || !alive.current) return;
    busy.current = true; setSaving(true); setError('');
    try {
      while (alive.current && saved.current !== change.current) {
        const snapshot = latest.current;
        const generation = change.current;
        const response = await api.put(`/reader/${resourceId}/state`, { ...snapshot, version: revision.current });
        revision.current = response.data.version;
        saved.current = generation;
      }
    } catch (reason: any) {
      if (alive.current) {
        if (reason.response?.status === 409) { blocked.current = true; setConflict(true); }
        setError(libraryError(reason, 'Changes are not saved. Retry before leaving this page.'));
      }
    } finally { busy.current = false; if (alive.current) setSaving(false); }
  }, [resourceId]);

  const update = (next: SyncedReaderState) => {
    if (!ready || blocked.current) return;
    latest.current = next; change.current += 1; setData(next); void flush();
  };
  return { data, update, ready, saving, error, conflict, retry: flush };
}
