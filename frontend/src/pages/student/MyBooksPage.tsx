import React, { useState, useEffect, useRef } from 'react';
import api from '../../services/api';
import { Link, useSearchParams } from 'react-router-dom';
import { libraryDate, libraryError } from '../../utils/library';
import BookCover from '../../components/BookCover';
import { BorrowRecord, Reservation } from '../../types';
import { BookOpen, Calendar, Clock, CheckCircle2, RotateCcw, AlertCircle, Bookmark } from 'lucide-react';

export default function MyBooksPage() {
  const requestVersion = useRef(0);
  const [params, setParams] = useSearchParams();
  const activeTab = ['reservations', 'history'].includes(params.get('tab') || '') ? params.get('tab') : 'borrows';
  const setActiveTab = (tab: string) => setParams(tab === 'borrows' ? {} : { tab });
  const [borrows, setBorrows] = useState<BorrowRecord[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchData();
    const refresh=()=>void fetchData();window.addEventListener('focus',refresh);
    return () => { requestVersion.current += 1;window.removeEventListener('focus',refresh); };
  }, []);

  const fetchData = async () => {
    const version = ++requestVersion.current;
    setIsLoading(true);
    setLoadError(null);
    try {
      const [borrowsRes, resvRes] = await Promise.all([
        api.get('/borrows/my'),
        api.get('/reservations/my'),
      ]);
      if (version !== requestVersion.current) return;
      setBorrows(borrowsRes.data || []);
      setReservations(resvRes.data || []);
    } catch (err) {
      if (version !== requestVersion.current) return;
      setLoadError(libraryError(err, 'Unable to load your library. Please try again.'));
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  };

  const handleReservation = async (reservation: Reservation) => {
    if (pendingAction || reservation.status!=='pending') return;
    setPendingAction(`reservation-${reservation.id}`);
    setMessage(null);
    try {
      await api.delete(`/reservations/${reservation.id}`);
      setMessage({ type: 'success', text: 'Reservation cancelled.' });
      await fetchData();
    } catch (error) {
      setMessage({ type: 'error', text: libraryError(error, 'Unable to update this reservation. Please try again.') });
    } finally { setPendingAction(null); }
  };

  const activeBorrows = borrows.filter((b) => b.status === 'borrowed').sort((a, b) => libraryDate(a.due_date).getTime() - libraryDate(b.due_date).getTime());
  const pastBorrows = borrows.filter((b) => b.status === 'returned');
  const activeReservations = reservations.filter(item => ['pending', 'ready'].includes(item.status));
  const completedReservations = reservations.filter(item => ['cancelled','fulfilled'].includes(item.status));
  const overdueCount = activeBorrows.filter(item => libraryDate(item.due_date) < new Date()).length;

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" /> My Library
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Staff issue and return your physical books. This page refreshes when you return to the window.
        </p>

        {/* Tab switch */}
        <div className="flex flex-wrap items-center gap-3 mt-6" aria-label="Library categories">
          <button
            onClick={() => setActiveTab('borrows')}
            aria-pressed={activeTab === 'borrows'}
            className={`px-5 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'borrows'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]'
                : 'bg-[#172033] text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            Borrowed {isLoading || loadError ? '' : `(${activeBorrows.length})`}
          </button>
          <button
            onClick={() => setActiveTab('reservations')}
            aria-pressed={activeTab === 'reservations'}
            className={`px-5 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'reservations'
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]'
                : 'bg-[#172033] text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            Reserved {isLoading || loadError ? '' : `(${activeReservations.length})`}
          </button>
          <button aria-pressed={activeTab === 'history'} onClick={() => setActiveTab('history')} className={`px-5 py-2.5 rounded-xl text-xs font-semibold ${activeTab === 'history' ? 'bg-blue-600 text-white' : 'bg-[#172033] text-gray-400 border border-gray-800'}`}>Returned history {isLoading || loadError ? '' : `(${pastBorrows.length})`}</button>
        </div>
        {!isLoading && !loadError && overdueCount > 0 && <p className="text-amber-400 text-sm mt-4">{overdueCount} {overdueCount === 1 ? 'loan is' : 'loans are'} overdue. Please return these books as soon as possible.</p>}
        <button onClick={()=>void fetchData()} disabled={isLoading} className="text-blue-400 text-sm mt-4 mr-4">Refresh status</button>
        <Link to="/books" className="inline-block text-blue-400 text-sm mt-4 hover:underline">Discover your next book →</Link>
      </div>

      {/* Message Banner */}
      {message && (
        <div
          role={message.type === 'error' ? 'alert' : 'status'}
          className={`p-4 rounded-xl text-sm flex items-center gap-2.5 ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-400'
          }`}
        >
          {message.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <span>{message.text}</span>
        </div>
      )}

      {loadError && <div role="alert" className="p-4 border border-red-500/30 rounded-xl text-red-400">{loadError} <button onClick={fetchData} className="underline ml-2">Retry</button></div>}
      {isLoading && <p role="status" className="text-gray-400">Loading your library…</p>}

      {/* Tab 1: Borrows */}
      {!isLoading && !loadError && activeTab === 'borrows' && (
        <div className="space-y-8">
          {/* Active Loans */}
          <div>
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" /> Active Loans
            </h2>

            {isLoading ? (
              <div className="h-40 bg-[#111827]/40 rounded-2xl animate-pulse" />
            ) : activeBorrows.length === 0 ? (
              <div className="text-center py-12 bg-[#111827]/40 border border-gray-800/60 rounded-2xl">
                <BookOpen className="w-10 h-10 text-gray-600 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">You currently have no borrowed books.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {activeBorrows.map((borrow) => {
                  const dueDate = libraryDate(borrow.due_date);
                  const isOverdue = dueDate < new Date();

                  return (
                    <div
                      key={borrow.id}
                      data-borrow-id={borrow.id}
                      className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-5 flex flex-col justify-between hover:border-blue-500/40 transition"
                    >
                      <div>
                        {borrow.book && <BookCover book={borrow.book} className="w-24 h-32 mb-4" />}
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div>
                            <Link to={`/books/${borrow.book_id}`} className="text-white font-bold text-base hover:text-blue-400">{borrow.book?.title || 'Catalog entry unavailable'}</Link>
                            <p className="text-xs text-gray-400">{borrow.book?.author}</p>
                          </div>
                          <span
                            className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                              isOverdue
                                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                                : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            }`}
                          >
                            {isOverdue ? 'Overdue' : 'Active'}
                          </span>
                        </div>

                        <div className="space-y-1.5 text-xs text-gray-400 my-4 bg-[#172033]/60 p-3 rounded-xl border border-gray-800">
                          <div className="flex justify-between">
                            <span>Borrowed:</span>
                            <span className="text-gray-200">
                              {libraryDate(borrow.borrowed_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="flex justify-between font-semibold">
                            <span>Due Date:</span>
                            <span className={isOverdue ? 'text-red-400' : 'text-blue-400'}>
                              {dueDate.toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>

                      <p className="text-xs text-blue-300">Return this copy at the library desk. Staff will update your loan.</p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      )}

      {!isLoading && !loadError && activeTab === 'history' && <div className="space-y-6">
          {pastBorrows.length === 0 && <p className="p-8 text-gray-400 border border-gray-800 rounded-xl">Your returned books will appear here. Returning a book does not mark it as read.</p>}
          {pastBorrows.length > 0 && (
            <div>
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" /> Returned books
              </h2>
              <div className="bg-[#111827]/60 border border-gray-800/60 rounded-2xl divide-y divide-gray-800">
                {pastBorrows.map((b) => (
                  <div key={b.id} className="p-4 flex items-center justify-between text-sm">
                    <div>
                      <Link to={`/books/${b.book_id}`} className="text-white font-medium hover:text-blue-400">{b.book?.title || 'Catalog entry unavailable'}</Link>
                      <p className="text-xs text-gray-500">{b.book?.author}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-emerald-400 font-medium">Returned</span>
                      <p className="text-[11px] text-gray-500">
                        {b.returned_at ? libraryDate(b.returned_at).toLocaleDateString() : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {completedReservations.length > 0 && <section><h2 className="text-white font-semibold mb-3">Reservation history</h2>{completedReservations.map(item => <p key={item.id} className="text-sm text-gray-400 py-2"><Link to={`/books/${item.book_id}`} className="text-blue-400">{item.book?.title || 'Catalog entry unavailable'}</Link> · {item.status==='fulfilled'?'Fulfilled — book issued':'Cancelled'}</p>)}</section>}
        </div>
      }

      {/* Tab 2: Reservations */}
      {!isLoading && !loadError && activeTab === 'reservations' && (
        <div>
          {activeReservations.length === 0 ? (
            <div className="text-center py-12 bg-[#111827]/40 border border-gray-800/60 rounded-2xl">
              <Bookmark className="w-10 h-10 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-400 text-sm">You have no pending book reservations.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {activeReservations.map((r) => (
                <div
                  key={r.id}
                  data-reservation-id={r.id}
                  className="bg-[#111827]/80 border border-gray-800/80 rounded-2xl p-5 flex flex-col justify-between"
                >
                  <div>
                    <Link to={`/books/${r.book_id}`} className="text-white font-bold text-base hover:text-blue-400">{r.book?.title || 'Catalog entry unavailable'}</Link>
                    <p className="text-xs text-gray-400 mt-0.5">{r.book?.author}</p>
                    <div className="mt-3">
                      <span className="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                        {r.status === 'ready' ? 'Ready for pickup' : 'Pending — waiting for a copy'}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-4">
                    Reserved on {libraryDate(r.created_at).toLocaleDateString()}
                  </p>
                  {r.status==='pending'?<button disabled={pendingAction !== null} onClick={() => handleReservation(r)} className="mt-4 py-2 px-3 rounded-xl text-sm bg-blue-600 text-white disabled:opacity-50">{pendingAction === `reservation-${r.id}` ? 'Saving…' : 'Cancel reservation'}</button>:<p className="text-sm text-blue-300 mt-4">Visit the library desk to collect your reserved copy.</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
