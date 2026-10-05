import { useState } from 'react';
import { BookOpen, Copy, Check, Download, Loader2, Sparkles } from 'lucide-react';
import api from '../services/api';
import { libraryError } from '../utils/library';

const modes = [
  ['short', 'Short Summary'], ['detailed', 'Detailed Summary'], ['key_points', 'Key Points'],
  ['simple', 'Explain Simply'], ['exam_notes', 'Exam Notes'],
] as const;
type Mode = typeof modes[number][0];
interface Summary { title: string | null; mode: Mode; summary: string; input_characters: number; truncated: boolean; model: string; processing_time: number; chunks: number; warnings: string[] }
const field = 'w-full rounded-xl border border-gray-700 bg-[#0b1220] px-4 py-3 text-sm text-gray-100 focus:outline-none focus:border-blue-500';

export default function BookSummarizer() {
  const [source, setSource] = useState<'text' | 'file'>('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<Mode>('detailed');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<Summary | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState('');

  async function generate(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setError('');
    if (source === 'text' && text.trim().length < 50) return setError('Enter at least 50 characters of content.');
    if (source === 'file') {
      if (!file) return setError('Choose a PDF or TXT file.');
      if (!/\.(pdf|txt)$/i.test(file.name)) return setError('Upload a PDF or TXT file.');
      if (!file.size) return setError('The selected file is empty.');
      if (file.size > 25 * 1024 * 1024) return setError('The file exceeds the 25 MB limit.');
    }
    setBusy(true);
    setResult(null);
    setCopied(false);
    setCopyError('');
    try {
      let response;
      if (source === 'file' && file) {
        const data = new FormData();
        data.append('file', file);
        data.append('mode', mode);
        if (title.trim()) data.append('title', title.trim());
        response = await api.post<Summary>('/ai/summarize/file', data, {
          headers: { 'Content-Type': 'multipart/form-data' }, timeout: 720000,
        });
      } else {
        response = await api.post<Summary>('/ai/summarize/text', { text, title: title.trim() || null, mode }, { timeout: 720000 });
      }
      setResult(response.data);
    } catch (err) {
      setError(libraryError(err, 'The summary could not be generated. Please try again.'));
    } finally { setBusy(false); }
  }

  async function copy() {
    if (!result) return;
    try { await navigator.clipboard.writeText(result.summary); setCopied(true); setCopyError(''); }
    catch { setCopyError('Copy is unavailable. Select the summary text or download it.'); }
  }
  function download() {
    if (!result) return;
    const url = URL.createObjectURL(new Blob([`${result.title || 'Book Summary'}\n\n${result.summary}`], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url; link.download = 'book-bridge-summary.txt'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <section className="space-y-6 pb-12">
      <div className="rounded-2xl border border-blue-500/20 bg-gradient-to-br from-[#152442] to-[#111827] p-6 sm:p-8">
        <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-blue-300"><BookOpen size={18} /> Read • Understand • Revise</div>
        <h1 className="text-2xl font-bold text-white sm:text-3xl">Book Summarizer</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-300">Turn a chapter, lecture note, or reading passage into focused study material. Add the content you want to understand, then choose your summary style.</p>
      </div>
      <form onSubmit={generate} className="space-y-5 rounded-2xl border border-gray-800 bg-[#111827]/80 p-5 sm:p-6">
        <fieldset disabled={busy} className="space-y-5 disabled:opacity-60">
          <legend className="mb-4 text-lg font-semibold text-white">Choose your content</legend>
          <div className="flex gap-2" aria-label="Content source">
            {(['text', 'file'] as const).map(value => <button key={value} type="button" aria-pressed={source === value} onClick={() => { setSource(value); setError(''); }} className={`rounded-xl border px-4 py-2 text-sm ${source === value ? 'border-blue-500/50 bg-blue-600/20 text-blue-200' : 'border-gray-700 text-gray-400'}`}>{value === 'text' ? 'Paste text' : 'Upload file'}</button>)}
          </div>
          <label className="block text-sm text-gray-300">Title <span className="text-gray-500">(optional)</span><input className={`${field} mt-2`} maxLength={300} value={title} onChange={e => setTitle(e.target.value)} placeholder="e.g. Introduction to operating systems" /></label>
          {source === 'text' ? <label className="block text-sm text-gray-300">Reading passage
            <textarea className={`${field} mt-2 min-h-56 resize-y leading-relaxed`} value={text} onChange={e => setText(e.target.value)} maxLength={1000000} placeholder="Paste at least 50 characters from your source material…" />
            <span className="mt-2 block text-xs text-gray-500">{text.length.toLocaleString()} / 1,000,000 characters · Minimum 50</span>
          </label> : <label className="block rounded-xl border border-dashed border-gray-600 bg-[#0b1220] p-5 text-sm text-gray-300">PDF or TXT document
            <input type="file" accept=".pdf,.txt,application/pdf,text/plain" className="mt-3 block w-full min-w-0 text-xs file:mr-3 file:rounded-lg file:border-0 file:bg-blue-600/20 file:px-3 file:py-2 file:text-blue-300" onChange={e => { setFile(e.target.files?.[0] || null); setError(''); }} />
            <span className="mt-3 block text-xs leading-relaxed text-gray-500">Up to 25 MB. Text-based PDFs and UTF-8 TXT files. Long documents are processed in sections. Up to 1,000,000 extracted characters; larger documents must be split into chapters.</span>
          </label>}
          <label className="block text-sm text-gray-300">Summary type<select className={`${field} mt-2`} value={mode} onChange={e => setMode(e.target.value as Mode)}>{modes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        </fieldset>
        <p className="text-xs leading-relaxed text-gray-500">Your content is processed locally on the Book Bridge server, without cloud AI calls. Book Bridge does not save the uploaded document. Summaries cover only the content you provide; check important details against the source.</p>
        {error && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">{error}</p>}
        <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60 sm:w-auto">{busy ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}{busy ? 'Generating summary…' : 'Generate Summary'}</button>
        {busy && <p role="status" className="text-sm text-blue-300">Analyzing document locally… The first request loads the model. Long chapters can take several minutes; keep this page open.</p>}
      </form>
      {result && <article aria-label="Generated summary" className="rounded-2xl border border-gray-700 bg-[#111827] p-5 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-800 pb-5">
          <div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-widest text-blue-400">{modes.find(([value]) => value === result.mode)?.[1]}</p><h2 className="mt-2 break-words text-xl font-bold text-white">{result.title || 'Your summary'}</h2><p className="mt-2 text-xs text-gray-500">{result.model} · {result.chunks} section(s) · {result.processing_time.toFixed(1)}s · {result.input_characters.toLocaleString()} source characters</p></div>
          <div className="flex gap-3 text-sm text-blue-300"><button type="button" onClick={copy} className="flex items-center gap-1.5">{copied ? <Check size={16} /> : <Copy size={16} />}{copied ? 'Copied' : 'Copy'}</button><button type="button" onClick={download} className="flex items-center gap-1.5"><Download size={16} />Download</button></div>
        </div>
        {result.warnings?.map(warning => <p key={warning} className="mt-4 rounded-xl bg-amber-500/10 p-3 text-sm text-amber-200">{warning}</p>)}
        {copyError && <p role="alert" className="mt-3 text-sm text-amber-200">{copyError}</p>}
        <div className="mt-6 whitespace-pre-wrap break-words text-sm leading-8 text-gray-200">{result.summary}</div>
      </article>}
    </section>
  );
}
