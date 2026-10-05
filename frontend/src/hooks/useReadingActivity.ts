import { useEffect, useRef, useState } from 'react';
import api from '../services/api';
export function useReadingActivity(resourceId: number, page: number, enabled: boolean) {
  const currentPage = useRef(page); currentPage.current = page;
  const [status, setStatus] = useState('');
  useEffect(() => {
    if (!enabled) return;
    let live = true, busy = false, sequence = 0, session = '';
    let timer: ReturnType<typeof setInterval> | undefined;
    let lastInteraction = Date.now();
    const interact = () => { lastInteraction = Date.now(); };
    const events = ['pointerdown', 'keydown', 'wheel', 'touchstart'];
    events.forEach(event => window.addEventListener(event, interact, { passive: true }));
    api.post(`/reading/sessions/${resourceId}`).then(r => {
      if (!live) return;
      session = r.data.session_id;
      setStatus('Reading activity enabled. Stay active in this tab; ten pages or fifteen minutes qualify.');
      timer = setInterval(async () => {
        if (busy || !live) return;
        busy = true;
        try {
          const result = await api.post(`/reading/sessions/${session}/heartbeat`, {
            sequence: sequence + 1, page: currentPage.current,
            active: document.visibilityState === 'visible' && document.hasFocus() && Date.now() - lastInteraction < 60000,
          });
          sequence = result.data.sequence;
          if (live && result.data.qualified) setStatus('Today’s meaningful reading goal is complete.');
        } catch (error: any) {
          if (live) setStatus(error.response?.status === 409 ? 'Reading tracking paused: another reader session may be open. Reopen this document to resume.' : 'Reading tracking is temporarily unavailable. Your bookmarks are unaffected.');
          if (error.response?.status === 409 && timer) clearInterval(timer);
        } finally { busy = false; }
      }, 15000);
    }).catch(() => { if (live) setStatus('Reading rewards are available for verified library-uploaded PDFs.'); });
    return () => { live = false; if (timer) clearInterval(timer); events.forEach(event => window.removeEventListener(event, interact)); };
  }, [resourceId, enabled]);
  return status;
}
