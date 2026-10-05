import { useReadingActivity } from '../hooks/useReadingActivity';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Document, Outline, Page, pdfjs } from 'react-pdf';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { ChevronLeft, ChevronRight, Highlighter, Trash2 } from 'lucide-react';
import { useReaderState } from '../hooks/useReaderState';
import type { ReaderHighlight } from '../hooks/useReaderState';
import { parseReaderState, readerKey } from '../utils/reader';
import type { ReaderState } from '../utils/reader';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
const options = { cMapUrl: `${import.meta.env.BASE_URL}pdfjs/cmaps/`, cMapPacked: true, standardFontDataUrl: `${import.meta.env.BASE_URL}pdfjs/standard_fonts/`, wasmUrl: `${import.meta.env.BASE_URL}pdfjs/wasm/`, isEvalSupported: false };
const button = 'rounded-xl border border-gray-700 bg-[#172033] px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-40';
const input = 'w-full rounded-xl bg-[#172033] border border-gray-700 p-2 text-sm text-white';

export default function PdfWorkspace({ url, resourceId, userId, token }: { url: string; resourceId: number; userId: number; token?: string }) {
  const source = useMemo(() => token ? { url, httpHeaders: { Authorization: `Bearer ${token}` } } : url, [url, token]);
  const { data, update, ready, saving, error, conflict, retry } = useReaderState(resourceId);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [pdfError, setPdfError] = useState('');
  const [outlineEmpty, setOutlineEmpty] = useState(false);
  const [pageInput, setPageInput] = useState('1');
  const [zoom, setZoom] = useState(100);
  const [width, setWidth] = useState(700);
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [selection, setSelection] = useState<Omit<ReaderHighlight, 'id' | 'note'> | null>(null);
  const [legacy, setLegacy] = useState<ReaderState | null>(null);
  const [changedDocument, setChangedDocument] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);
  const pageElement = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(readerKey(userId, String(resourceId)));
      if (raw) setLegacy(parseReaderState(raw));
    } catch { setMessage('Older browser bookmarks could not be read. Your server data is unaffected.'); }
  }, [userId, resourceId]);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(entries => setWidth(Math.max(180, Math.min(1000, entries[0].contentRect.width - 24))));
    observer.observe(element);
    return () => observer.disconnect();
  }, [ready]);
  useEffect(() => {
    if (!pdf || !ready || initialized.current) return;
    initialized.current = true;
    const fingerprint = pdf.fingerprints[0] || '';
    if (data.document_key && data.document_key !== fingerprint) { setChangedDocument(true); return; }
    const invalidPages = [...data.bookmarks, ...data.highlights].some(item => item.page > pdf.numPages);
    if (invalidPages) { setChangedDocument(true); return; }
    if (data.total_pages !== pdf.numPages || data.document_key !== fingerprint || data.page > pdf.numPages) {
      update({ ...data, page: Math.min(data.page, pdf.numPages), total_pages: pdf.numPages, document_key: fingerprint });
    }
  }, [pdf, ready, data, update]);
  useEffect(() => { setPageInput(String(data.page)); setSelection(null); setNote(data.bookmarks.find(item => item.page === data.page)?.note || ''); }, [data.page]);
  // Loading server bookmarks can restore page 1 without changing page number.
  useEffect(() => { if (ready) setNote(data.bookmarks.find(item => item.page === data.page)?.note || ''); }, [ready]);

  const readingStatus = useReadingActivity(resourceId, data.page, ready && !!pdf && !changedDocument && !pdfError);

  const disabled = !ready || !pdf || saving || conflict || changedDocument || !!pdfError;
  const go = (page: number) => {
    if (!pdf || !Number.isInteger(page) || page < 1 || page > pdf.numPages) { setMessage(`Enter a page from 1 to ${pdf?.numPages || 1}.`); return; }
    setSelection(null); setMessage(''); update({ ...data, page });
    viewport.current?.scrollTo({ top: 0, left: 0 });
  };
  const captureSelection = () => {
    const selected = window.getSelection();
    const holder = pageElement.current;
    if (!selected || !holder || selected.isCollapsed || !selected.rangeCount) return;
    const range = selected.getRangeAt(0);
    if (!holder.contains(range.startContainer) || !holder.contains(range.endContainer)) return;
    const text = selected.toString().trim();
    if (!text || text.length > 4000) { setMessage('Select up to 4,000 characters on this page.'); return; }
    const bounds = holder.getBoundingClientRect();
    const rects = Array.from(range.getClientRects()).filter(r => r.width > 0 && r.height > 0).map(r => {
      const x = Math.max(0, (r.left-bounds.left)/bounds.width);
      const y = Math.max(0, (r.top-bounds.top)/bounds.height);
      return { x, y, width: Math.min(1-x, r.width/bounds.width), height: Math.min(1-y, r.height/bounds.height) };
    }).filter(r => r.width > 0 && r.height > 0);
    if (!rects.length || rects.length > 100) { setMessage('Select a shorter passage to highlight.'); return; }
    setSelection({ page: data.page, text, rects });
  };
  const addHighlight = () => {
    if (!selection) return;
    if (data.highlights.length >= 200) { setMessage('Remove a highlight before adding more than 200.'); return; }
    update({ ...data, highlights: [...data.highlights, { ...selection, id: crypto.randomUUID(), note: '' }] });
    setSelection(null); window.getSelection()?.removeAllRanges();
  };
  const bookmark = () => {
    if (data.bookmarks.length >= 200 && !data.bookmarks.some(b => b.page === data.page)) { setMessage('Remove a bookmark before adding more than 200.'); return; }
    update({ ...data, bookmarks: [...data.bookmarks.filter(b => b.page !== data.page), { page: data.page, note }].sort((a,b) => a.page-b.page) });
  };
  const importLegacy = () => {
    if (!legacy || !pdf) return;
    if (legacy.page > pdf.numPages || legacy.bookmarks.some(b => b.page > pdf.numPages)) { setMessage('Older bookmarks contain pages outside this PDF. They remain in browser storage; no data was imported.'); return; }
    const bookmarks = new Map(data.bookmarks.map(b => [b.page, b]));
    for (const b of legacy.bookmarks) if (!bookmarks.has(b.page)) bookmarks.set(b.page, b);
    if (bookmarks.size > 200) { setMessage('Import would exceed the 200 bookmark limit.'); return; }
    update({ ...data, page: legacy.page, bookmarks: [...bookmarks.values()].sort((a,b) => a.page-b.page) });
    setMessage('Older bookmarks imported; existing server notes were kept. The browser copy remains available.'); setLegacy(null);
  };

  return <div className="space-y-3">
    <div className="rounded-2xl border border-gray-800 bg-[#111827] p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button className={button} aria-label="Previous page" disabled={disabled || data.page <= 1} onClick={() => go(data.page-1)}><ChevronLeft size={18} /></button>
        <form className="flex items-center gap-2" onSubmit={e => { e.preventDefault(); if (!disabled) go(Number(pageInput)); }}>
          <label className="text-sm text-gray-300" htmlFor="pdf-page">Page</label><input id="pdf-page" type="number" min="1" max={pdf?.numPages || 1} value={pageInput} onChange={e => setPageInput(e.target.value)} className={`${input} !w-20`} disabled={disabled} />
          <span className="text-sm text-gray-400">of {pdf?.numPages ?? '—'}</span><button className={button} disabled={disabled}>Go</button>
        </form>
        <button className={button} aria-label="Next page" disabled={disabled || data.page >= (pdf?.numPages || 1)} onClick={() => go(data.page+1)}><ChevronRight size={18} /></button>
        <label className="text-sm text-gray-400">Zoom <select aria-label="Zoom" value={zoom} onChange={e => { setSelection(null); setZoom(Number(e.target.value)); }} className={button}><option value={75}>75%</option><option value={100}>Fit width</option><option value={125}>125%</option><option value={150}>150%</option></select></label>
        <label className="text-sm text-gray-400">Theme <select aria-label="Reading theme" value={data.theme} disabled={disabled} onChange={e => update({ ...data, theme: e.target.value as typeof data.theme })} className={button}><option value="light">Paper</option><option value="sepia">Sepia</option><option value="dark">Night</option></select></label>
      </div>
      <div role="status" className="text-xs text-cyan-300">{!ready ? 'Loading your reading data…' : saving ? 'Saving to your account…' : error ? 'Changes are not synced.' : 'Synced to your account. Page changes save automatically.'}</div>
      {readingStatus && <p role="status" className="text-xs text-slate-400">{readingStatus}</p>}
      {pdf && <progress aria-label="Reading position" value={Math.min(data.page,pdf.numPages)} max={pdf.numPages} className="w-full h-1 accent-cyan-400" />}
      {error && <div role="alert" className="text-amber-300 text-sm">{error} {ready && !conflict && <button className={button} onClick={retry}>Retry sync</button>}<button className={button} onClick={() => window.location.reload()}>Reload saved data</button></div>}
      {changedDocument && <p role="alert" className="text-amber-300 text-sm">This PDF has changed since your notes were saved. Existing notes are preserved; editing and automatic saving are paused to avoid moving highlights onto the wrong text.</p>}
    </div>
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div ref={viewport} className="min-w-0 max-h-[75vh] overflow-auto bg-[#0a0f1d] rounded-2xl border border-gray-800 p-3" aria-label="PDF pages">
        {ready && <Document file={source} options={options} onLoadSuccess={setPdf} onLoadError={() => setPdfError('This PDF could not be loaded. The provider may block access from Book Bridge, or the file may be invalid. Use Open original to read it.')} onSourceError={() => setPdfError('Unable to fetch this PDF. Use Open original.')} onPassword={(_callback, _reason) => setPdfError('This PDF requires a password. Use Open original to open the protected document.')} loading={<p className="text-gray-400">Loading PDF…</p>} error={<p className="text-red-300">PDF unavailable.</p>}>
          {pdf && <div ref={pageElement} className="relative w-fit" onMouseUp={captureSelection} onTouchEnd={captureSelection} onKeyUp={captureSelection}>
            <div style={{ filter: data.theme === 'sepia' ? 'sepia(0.65)' : data.theme === 'dark' ? 'invert(0.9) hue-rotate(180deg)' : undefined }}>
              <Page pageNumber={Math.min(data.page,pdf.numPages)} width={width * zoom / 100} renderTextLayer renderAnnotationLayer={false} onRenderError={() => setPdfError('This page could not be rendered. Use Open original.')} />
            </div>
            {!changedDocument && data.highlights.filter(h => h.page === data.page).flatMap(h => h.rects.map((r,index) => <div key={`${h.id}:${index}`} data-reader-highlight={h.id} aria-hidden="true" className="absolute pointer-events-none bg-yellow-400/30" style={{ left:`${r.x*100}%`,top:`${r.y*100}%`,width:`${r.width*100}%`,height:`${r.height*100}%` }} />))}
          </div>}
        </Document>}
        {pdfError && <p role="alert" className="text-red-300 p-3">{pdfError}</p>}
      </div>
      <aside className="bg-[#111827] border border-gray-800 rounded-2xl p-4 space-y-4 min-w-0">
        <h2 className="text-white font-semibold">Reading tools</h2>
        <p className="text-xs text-gray-400">Private to your account and synced across devices. Text selection requires a text-based PDF; scanned pages need OCR.</p>
        {legacy && <button className={button} onClick={importLegacy} disabled={disabled}>Import older browser bookmarks</button>}
        <details><summary className="text-sm text-cyan-400 cursor-pointer">Chapters</summary>{pdf && <Outline pdf={pdf} className="text-xs text-gray-300 break-words [&_a]:text-cyan-400 [&_li]:my-2" onItemClick={({pageNumber}) => { if (!disabled) go(pageNumber); }} onLoadSuccess={items => setOutlineEmpty(!items?.length)} onLoadError={() => setOutlineEmpty(true)} />}{outlineEmpty && <p className="text-xs text-gray-400">This PDF has no chapter outline. Use page navigation or bookmarks.</p>}</details>
        <label htmlFor="page-note" className="block text-sm text-gray-300">Note for page {data.page}</label>
        <textarea id="page-note" className={input} rows={3} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} />
        <button className={button} disabled={disabled} onClick={bookmark}>{data.bookmarks.some(b => b.page === data.page) ? 'Update bookmark' : 'Add bookmark'}</button>
        <ul className="space-y-2 max-h-48 overflow-auto" aria-label="Bookmarks">{data.bookmarks.map(b => <li key={b.page} className="border border-gray-700 rounded-xl p-2"><div className="flex justify-between gap-2"><button className="text-cyan-400 text-sm" disabled={disabled} onClick={() => go(b.page)}>Page {b.page}</button><button aria-label={`Remove bookmark for page ${b.page}`} disabled={disabled} onClick={() => update({...data,bookmarks:data.bookmarks.filter(item=>item.page!==b.page)})}><Trash2 size={15} className="text-gray-400" /></button></div>{b.note && <p className="whitespace-pre-wrap break-words text-xs text-gray-300 mt-2">{b.note}</p>}</li>)}</ul>
        {!data.bookmarks.length && <p className="text-xs text-gray-500">No bookmarks yet.</p>}
        <div><h3 className="text-white text-sm font-semibold">Highlights</h3><p className="text-xs text-gray-400 mt-1">Select text on the page, then save the highlight.</p></div>
        {selection && <p className="text-xs text-gray-300 break-words">Selected: {selection.text.slice(0,180)}</p>}
        <button className={button} disabled={disabled || !selection} onClick={addHighlight}><Highlighter size={14} className="inline mr-2" />Save highlight</button>
        <ul aria-label="Highlights" className="space-y-3 max-h-80 overflow-auto">{data.highlights.map(h => <HighlightCard key={h.id} highlight={h} disabled={disabled} onGo={() => go(h.page)} onDelete={() => update({...data,highlights:data.highlights.filter(item=>item.id!==h.id)})} onSave={note => update({...data,highlights:data.highlights.map(item=>item.id===h.id?{...item,note}:item)})} />)}</ul>
      </aside>
    </div>
    {message && <p role="status" className="text-sm text-cyan-300">{message}</p>}
  </div>;
}

function HighlightCard({highlight:h,disabled,onGo,onDelete,onSave}: {highlight:ReaderHighlight;disabled:boolean;onGo:()=>void;onDelete:()=>void;onSave:(note:string)=>void}) {
  const [note,setNote]=useState(h.note);
  return <li className="border border-gray-700 rounded-xl p-3 space-y-2"><div className="flex justify-between gap-2"><button className="text-cyan-400 text-xs" disabled={disabled} onClick={onGo}>Highlight on page {h.page}</button><button aria-label={`Remove highlight ${h.id}`} disabled={disabled} onClick={onDelete}><Trash2 size={15} className="text-gray-400" /></button></div><blockquote className="text-xs text-gray-300 break-words">{h.text}</blockquote><textarea aria-label={`Highlight note ${h.id}`} maxLength={2000} rows={2} className={input} value={note} onChange={e=>setNote(e.target.value)} /><button className={button} disabled={disabled} onClick={()=>onSave(note)}>Save highlight note</button></li>;
}
