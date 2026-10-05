import { useSearchParams } from 'react-router-dom';
import ContributionPanel from '../../components/ContributionPanel';
import React, { useState, useEffect } from 'react';
import { isAxiosError } from 'axios';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import type { Note } from '../../types';
import {
  FileText, Search, Download, Eye, Upload, Filter,
  Calendar, CheckCircle2, X, Plus, AlertCircle
} from 'lucide-react';

const MAX_FILE_SIZE = 25 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt']);

function getErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) return fallback;
  const detail: unknown = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (typeof item === 'object' && item !== null && 'msg' in item && typeof item.msg === 'string') {
        return [item.msg];
      }
      return [];
    });
    if (messages.length) return messages.join(' ');
  }
  return error.response ? fallback : 'Unable to reach the server. Please check your connection and try again.';
}

function validateFile(file: File): string | null {
  const extension = file.name.match(/\.([^.]+)$/)?.[1].toLowerCase();
  if (!extension || !ALLOWED_EXTENSIONS.has(extension)) {
    return 'Unsupported file type. Choose PDF, DOC, DOCX, PPT, PPTX, or TXT.';
  }
  if (file.size === 0) return 'The selected file is empty. Please choose a document with content.';
  if (file.size > MAX_FILE_SIZE) return 'Selected file exceeds maximum limit of 25 MB.';
  return null;
}

function getFullFileUrl(url?: string | null): string | undefined {
  if (!url?.trim()) return undefined;
  try {
    const base = new URL(api.defaults.baseURL || '/', window.location.origin);
    const resolved = new URL(url, base);
    return ['http:', 'https:'].includes(resolved.protocol) ? resolved.href : undefined;
  } catch {
    return undefined;
  }
}

export default function NotesPage() {
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const canUpload = user?.role === 'librarian' || user?.role === 'admin';
  const [personalUpload, setPersonalUpload] = useState(false);
  const [collection, setCollection] = useState<'library' | 'personal'>('library');
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('all');
  const [selectedSemester, setSelectedSemester] = useState('all');

  // Preview modal
  const [previewNote, setPreviewNote] = useState<Note | null>(null);

  // Upload modal
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSubject, setNewSubject] = useState('DBMS');
  const [newSemester, setNewSemester] = useState('5');
  const newBranch = 'Computer Science & Engineering';
  const [newDesc, setNewDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const listRequest = React.useRef(0);
  useEffect(() => {
    setNotes([]);
    void fetchNotes();
    return () => { listRequest.current += 1; };
  }, [collection, user?.id]);

  const fetchNotes = async () => {
    const request = ++listRequest.current;
    setIsLoading(true);
    setListError(null);
    try {
      const res = await api.get<Note[]>(collection === 'personal' ? '/notes/my' : '/notes/');
      if (request === listRequest.current) setNotes(res.data);
    } catch (err) {
      if (request === listRequest.current) setListError(getErrorMessage(err, 'Unable to load the notes catalog. Please try again.'));
    } finally {
      if (request === listRequest.current) setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchQuery.trim().toLowerCase());
  };

  // The catalog API is unpaginated; retain all subjects while combining filters locally.
  const subjects = ['all', ...Array.from(new Set(notes.map((note) => note.subject).filter(Boolean))).sort()];
  const visibleNotes = notes.filter((note) =>
    (selectedSubject === 'all' || note.subject === selectedSubject) &&
    (selectedSemester === 'all' || note.semester === Number(selectedSemester)) &&
    (!activeSearch || [note.title, note.description, note.subject].some((value) => value?.toLowerCase().includes(activeSearch)))
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const error = validateFile(file);
      if (error) {
        setUploadError(error);
        setSelectedFile(null);
        e.target.value = '';
        return;
      }
      setUploadError(null);
      setSelectedFile(file);
      // If title is empty, pre-fill from filename without extension
      if (!newTitle) {
        const cleanName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        setNewTitle(cleanName.slice(0, 255));
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isUploading) return;
    setUploadError(null);

    if (!canUpload && !personalUpload) {
      setUploadError('Only librarians and administrators can upload study material.');
      return;
    }

    if (!selectedFile) {
      setUploadError('Please choose a file (PDF, Word, or Document) to upload.');
      return;
    }

    if (!newTitle.trim() || !newSubject.trim()) {
      setUploadError('Title and Subject are required fields.');
      return;
    }

    const fileError = validateFile(selectedFile);
    if (fileError) {
      setUploadError(fileError);
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('title', newTitle.trim());
      formData.append('subject', newSubject.trim());
      formData.append('semester', newSemester);
      formData.append('branch', newBranch);
      if (newDesc.trim()) {
        formData.append('description', newDesc.trim());
      }
      formData.append('access_level', 'public');

      const res = await api.post<Note>(personalUpload ? '/notes/my/upload' : '/notes/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      listRequest.current += 1;
      setIsLoading(false);
      setCollection(personalUpload ? 'personal' : 'library');
      setNotes((current) => [res.data, ...current.filter((note) => note.id !== res.data.id && note.status === res.data.status)]);
      setSelectedSubject('all');
      setSelectedSemester('all');
      setSearchQuery('');
      setActiveSearch('');
      setListError(null);
      setUploadSuccess(true);
      setSelectedFile(null);
      setNewTitle('');
      setNewDesc('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      setShowUploadModal(false);
    } catch (err) {
      setUploadError(getErrorMessage(err, 'Upload failed. Please try again.'));
    } finally {
      setIsUploading(false);
    }
  };

  const downloadPersonal = async (note: Note) => {
    setDownloadError(null);
    try {
      const response = await api.get(`/notes/personal-files/${encodeURIComponent(note.file_url?.split('/').pop() || '')}`, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${note.title.replace(/[\\/:*?"<>|]/g, '_')}.${(note.file_type || 'txt').toLowerCase()}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setDownloadError('Unable to download your note. Please try again.');
    }
  };

  const handleDownload = async (noteId: number) => {
    setDownloadError(null);
    try {
      const res = await api.post<{ download_count: number }>(`/notes/${noteId}/download`);
      setNotes((current) => current.map((note) => note.id === noteId ? { ...note, download_count: res.data.download_count } : note));
      setPreviewNote((current) => current?.id === noteId ? { ...current, download_count: res.data.download_count } : current);
    } catch (err) {
      setDownloadError(getErrorMessage(err, 'The file was opened, but its download count could not be updated. Please try again.'));
    }
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* Top Banner */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="px-3 py-0.5 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Academic Resources
          </span>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-2 flex items-center gap-2.5">
            <FileText className="w-7 h-7 text-blue-400" /> Notes Library & Lecture Summaries
          </h1>
          <p className="text-gray-400 text-sm mt-1 max-w-xl">
            Access verified lecture notes, formula sheets, and study materials organized by branch and semester.
          </p>
        </div>

        <button onClick={() => { setPersonalUpload(true); setUploadSuccess(false); setUploadError(null); setShowUploadModal(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2.5 px-4 rounded-xl">
          Upload Private Note
        </button>
        {canUpload && (
          <button
            disabled={isLoading}
            onClick={() => {
              setPersonalUpload(false);
              setUploadSuccess(false);
              setUploadError(null);
              setShowUploadModal(true);
            }}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold py-2.5 px-4 rounded-xl transition flex items-center gap-1.5 shadow-[0_0_12px_rgba(37,99,235,0.4)] shrink-0 self-start md:self-auto"
          >
            <Plus className="w-4 h-4" /> Upload Study Material
          </button>
        )}
      </div>

        <details open={searchParams.get("view")==="submissions" || undefined} className="w-full rounded-xl border border-slate-700 p-4"><summary className="cursor-pointer text-sm text-blue-300">Submit to Library — notes and study materials</summary><div className="mt-4"><p className="mb-4 text-sm text-slate-400">Share a contribution with the library after librarian approval. For personal storage visible only to you, use Upload Private Note.</p><ContributionPanel section="notes" /></div></details>

      {uploadSuccess && (
        <div role="status" className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" /> {personalUpload ? 'Your private note was uploaded successfully.' : 'Study note published successfully to campus catalog!'}
        </div>
      )}

      {downloadError && (
        <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {downloadError}
        </div>
      )}

      <div className="flex gap-3 items-center flex-wrap">
        {(['library', 'personal'] as const).map((value) => <button key={value} onClick={() => { setCollection(value); setNotes([]); setSelectedSubject('all'); setSelectedSemester('all'); setActiveSearch(''); setSearchQuery(''); }}
          aria-pressed={collection === value} className={`px-4 py-2 rounded-xl text-sm ${collection === value ? 'bg-blue-600 text-white' : 'bg-slate-800 text-gray-300'}`}>
          {value === 'library' ? 'Library notes' : 'My notes'}
        </button>)}
        {collection === 'personal' && <span className="text-xs text-gray-400">Private uploads — only you can download these notes.</span>}
      </div>
      {/* Search and Filters */}
      <div className="bg-[#111827]/60 border border-gray-800/60 rounded-2xl p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Search */}
        <form onSubmit={handleSearch} className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            aria-label="Search notes"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes by title, topic, or keyword..."
            className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </form>

        {/* Subject and Semester Filters */}
        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          <div className="flex items-center gap-1 text-xs text-gray-400 mr-1">
            <Filter className="w-3.5 h-3.5" /> Filters:
          </div>

          <div className="flex flex-wrap gap-1.5">
            {subjects.map((subj) => (
              <button
                key={subj}
                onClick={() => setSelectedSubject(subj)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  selectedSubject === subj
                    ? 'bg-blue-600 text-white shadow'
                    : 'bg-[#172033] text-gray-300 hover:bg-gray-800'
                }`}
              >
                {subj === 'all' ? 'All Subjects' : subj}
              </button>
            ))}
          </div>

          <select
            aria-label="Filter by semester"
            value={selectedSemester}
            onChange={(e) => setSelectedSemester(e.target.value)}
            className="bg-[#172033] border border-gray-700/60 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none"
          >
            <option value="all">All Semesters</option>
            <option value="1">Semester 1</option>
            <option value="2">Semester 2</option>
            <option value="3">Semester 3</option>
            <option value="4">Semester 4</option>
            <option value="5">Semester 5</option>
            <option value="6">Semester 6</option>
            <option value="7">Semester 7</option>
            <option value="8">Semester 8</option>
          </select>
        </div>
      </div>

      {/* Notes Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-gray-500 text-sm">Loading notes catalog...</div>
      ) : listError ? (
        <div role="alert" className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
          <p>{listError}</p>
          <button onClick={() => void fetchNotes()} className="mt-2 underline font-semibold">Try again</button>
        </div>
      ) : visibleNotes.length === 0 ? (
        <div className="py-20 text-center text-gray-500 text-sm bg-[#111827]/40 rounded-2xl border border-gray-800/40">
          <FileText className="w-10 h-10 mx-auto text-gray-600 mb-2" />
          {collection === 'personal' ? 'No personal notes found. Upload Private Note or adjust your filters.' : 'No study notes match the selected filters. Try choosing "All Subjects".'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {visibleNotes.map((note) => (
            <div
              key={note.id}
              className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-5 flex flex-col justify-between hover:border-blue-500/40 transition group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    {note.subject || 'General'}
                  </span>
                  <span className="text-[10px] text-gray-500 flex items-center gap-1">
                    <Calendar className="w-3 h-3" /> {note.semester ? `Semester ${note.semester}` : 'Semester not specified'}
                  </span>
                </div>

                <h3 className="text-white font-bold text-sm line-clamp-2 group-hover:text-blue-400 transition">
                  {note.title}
                </h3>
                <p className="text-xs text-gray-400 line-clamp-3 mt-2 leading-relaxed">
                  {note.description || note.content || 'No description provided.'}
                </p>

                <div className="flex items-center gap-3 mt-4 text-[11px] text-gray-400">
                  <span className="bg-[#172033] px-2 py-0.5 rounded text-gray-300 font-mono">
                    {note.file_type || 'Document'} • {note.file_size || 'Size not available'}
                  </span>
                  <span>{note.status === 'personal' ? 'Private • Only you' : `${note.download_count ?? 0} downloads`}</span>
                </div>
              </div>

              <div className="mt-5 pt-3.5 border-t border-gray-800/80 flex items-center gap-2">
                <button
                  onClick={() => setPreviewNote(note)}
                  className="flex-1 bg-[#1e293b] hover:bg-gray-700 text-white text-xs font-semibold py-2 rounded-xl transition flex items-center justify-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5" /> Preview Summary
                </button>
                <a
                  href={getFullFileUrl(note.file_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Download ${note.title}`}
                  aria-disabled={!getFullFileUrl(note.file_url)}
                  tabIndex={getFullFileUrl(note.file_url) ? 0 : -1}
                  onClick={(event) => {
                    if (!getFullFileUrl(note.file_url)) {
                      event.preventDefault();
                      return;
                    }
                    if (note.status === 'personal') { event.preventDefault(); void downloadPersonal(note); }
                    else void handleDownload(note.id);
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold p-2 rounded-xl transition flex items-center justify-center aria-disabled:opacity-40 aria-disabled:cursor-not-allowed"
                  title={getFullFileUrl(note.file_url) ? 'Download File' : 'No document attached'}
                >
                  <Download className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {previewNote && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-2xl max-w-xl w-full p-6 space-y-4 animate-scaleIn">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-white text-base truncate">{previewNote.title}</h3>
              </div>
              <button aria-label="Close note preview" onClick={() => setPreviewNote(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">Subject:</span>
                <span className="text-blue-400 font-semibold">{previewNote.subject}</span>
                <span className="text-gray-600">•</span>
                <span className="text-gray-400">Semester:</span>
                <span className="text-white font-semibold">Semester {previewNote.semester}</span>
              </div>

              <div>
                <span className="text-gray-400 block mb-1 font-semibold">Overview & Content Description:</span>
                <p className="text-gray-300 bg-[#172033] p-3 rounded-xl leading-relaxed border border-gray-800">
                  {previewNote.description || previewNote.content}
                </p>
              </div>

              <div className="p-3 bg-blue-900/20 border border-blue-700/30 rounded-xl flex items-center gap-2 text-blue-300">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                <span>{previewNote.status === 'personal' ? 'Personal notes • Private to your account' : 'Library-published study material'}</span>
              </div>
            </div>

            {downloadError && (
              <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {downloadError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
              <button
                onClick={() => setPreviewNote(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Close
              </button>
              <a
                href={getFullFileUrl(previewNote.file_url)}
                target="_blank"
                rel="noopener noreferrer"
                aria-disabled={!getFullFileUrl(previewNote.file_url)}
                tabIndex={getFullFileUrl(previewNote.file_url) ? 0 : -1}
                onClick={(event) => {
                  if (!getFullFileUrl(previewNote.file_url)) {
                    event.preventDefault();
                    return;
                  }
                  if (previewNote.status === 'personal') { event.preventDefault(); void downloadPersonal(previewNote); }
                  else void handleDownload(previewNote.id);
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition flex items-center gap-1.5 shadow-md aria-disabled:opacity-40 aria-disabled:cursor-not-allowed"
                title={getFullFileUrl(previewNote.file_url) ? 'Download Full Document' : 'No document attached'}
              >
                <Download className="w-3.5 h-3.5" /> Download Full Document
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Upload Note Modal */}
      {showUploadModal && (canUpload || personalUpload) && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 animate-scaleIn">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                <Upload className="w-5 h-5 text-blue-400" /> {personalUpload ? 'Upload Private Note' : 'Upload Study Material'}
              </h3>
              <button aria-label="Close upload dialog" disabled={isUploading} onClick={() => setShowUploadModal(false)} className="text-gray-400 hover:text-white disabled:opacity-50">
                <X className="w-5 h-5" />
              </button>
            </div>

            {uploadError && (
              <div role="alert" className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" /> {uploadError}
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-3.5 text-xs">
              <div>
                <label htmlFor="note-title" className="block text-gray-400 font-semibold mb-1">Document Title *</label>
                <input
                  id="note-title"
                  type="text"
                  maxLength={255}
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Distributed Systems Final Review Notes"
                  required
                  className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor="note-subject" className="block text-gray-400 font-semibold mb-1">Subject *</label>
                  <input
                    id="note-subject"
                    type="text"
                    maxLength={100}
                    value={newSubject}
                    onChange={(e) => setNewSubject(e.target.value)}
                    required
                    className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label htmlFor="note-semester" className="block text-gray-400 font-semibold mb-1">Semester</label>
                  <select
                    id="note-semester"
                    value={newSemester}
                    onChange={(e) => setNewSemester(e.target.value)}
                    className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                      <option key={s} value={s}>Semester {s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="note-description" className="block text-gray-400 font-semibold mb-1">Description / Syllabus Units Covered</label>
                <textarea
                  id="note-description"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Summarize key topics, formulas, or theorems included..."
                  rows={2}
                  className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Functional File Selector */}
              <div>
                <label htmlFor="note-file" className="block text-gray-400 font-semibold mb-1">Select Document File *</label>
                <input
                  id="note-file"
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx,.ppt,.pptx,.txt"
                  className="hidden"
                />

                {selectedFile ? (
                  <div className="p-3 border border-blue-500/40 rounded-xl bg-blue-950/20 flex items-center justify-between">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <FileText className="w-5 h-5 text-blue-400 shrink-0" />
                      <div className="min-w-0">
                        <p className="text-white font-medium truncate text-xs">{selectedFile.name}</p>
                        <p className="text-[10px] text-gray-400">
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'Document'}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                      className="text-xs text-red-400 hover:text-red-300 font-semibold ml-2 px-2 py-1 rounded hover:bg-red-500/10 shrink-0"
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full p-4 border border-dashed border-gray-700 hover:border-blue-500/60 rounded-xl text-center bg-[#172033]/40 hover:bg-[#172033]/70 transition cursor-pointer"
                  >
                    <Upload className="w-6 h-6 mx-auto text-blue-400 mb-1" />
                    <span className="text-gray-300 font-medium block">Click to choose PDF or Document</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">Supports PDF, DOC, DOCX, PPT, PPTX, TXT (Max 25MB)</span>
                  </button>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
                <button
                  type="button"
                  disabled={isUploading}
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-4 py-2 rounded-xl transition flex items-center gap-2 shadow-[0_0_12px_rgba(37,99,235,0.4)]"
                >
                  {isUploading ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Uploading...</span>
                    </>
                  ) : (
                    <span>{personalUpload ? 'Upload private note' : 'Publish Note'}</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
