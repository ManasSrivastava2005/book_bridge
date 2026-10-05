import React, { useState, useEffect, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../../services/api';
import type { Book, BorrowRecord, Reservation, Library } from '../../types';
import BookCover from '../../components/BookCover';
import { libraryError, loanAction, libraryDate } from '../../utils/library';
import { Search, Filter, BookOpen, Star, CheckCircle, AlertCircle, Sparkles, ChevronRight } from 'lucide-react';

export default function BrowseBooksPage() {
  const requestVersion = useRef(0);
  const [books, setBooks] = useState<Book[]>([]);
  const [params, setParams] = useSearchParams();
  const searchQuery = params.get('search') || '';
  const selectedCategory = params.get('category') || 'All';
  const selectedLibrary = params.get('library') || 'all';
  const availableOnly = params.get('available') === 'true';
  const sortBy = params.get('sort') || 'newest';
  const reviewMode = params.get('view') === 'reviews';
  const [borrows, setBorrows] = useState<BorrowRecord[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [personalError, setPersonalError] = useState<string | null>(null);
  const [pendingBook, setPendingBook] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [borrowSuccess, setBorrowSuccess] = useState<string | null>(null);
  const [borrowError, setBorrowError] = useState<string | null>(null);

  const categories = ['All', ...Array.from(new Set(books.map(book => book.category).filter(Boolean))).sort()];
  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    fetchBooks();
    return () => { requestVersion.current += 1; };
  }, []);

  const fetchBooks = async () => {
    const version = ++requestVersion.current;
    setIsLoading(true);
    setLoadError(null);
    setPersonalError(null);
    try {
      const [catalog, loans, holds, campuses] = await Promise.allSettled([
        api.get<Book[]>('/books/discover'), api.get<BorrowRecord[]>('/borrows/my'),
        api.get<Reservation[]>('/reservations/my'), api.get<Library[]>('/libraries/'),
      ]);
      if (version !== requestVersion.current) return;
      if (catalog.status === 'rejected') throw catalog.reason;
      setBooks(catalog.value.data);
      if (loans.status === 'fulfilled') setBorrows(loans.value.data);
      if (holds.status === 'fulfilled') setReservations(holds.value.data);
      if (campuses.status === 'fulfilled') setLibraries(campuses.value.data);
      if (loans.status === 'rejected' || holds.status === 'rejected') setPersonalError('Your loans and reservations could not be loaded. Retry before reserving.');
    } catch (err) {
      if (version !== requestVersion.current) return;
      setLoadError(libraryError(err, 'Unable to load the catalog. Please try again.'));
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  };

  const filteredBooks = books.filter(book => {
    const query = searchQuery.trim().toLowerCase();
    return (selectedCategory === 'All' || book.category === selectedCategory)
      && (selectedLibrary === 'all' || book.library_id === Number(selectedLibrary))
      && (!availableOnly || book.available_copies > 0)
      && (!query || [book.title, book.author, book.category, book.isbn].some(value => value?.toLowerCase().includes(query)));
  }).sort((a, b) => sortBy === 'title' ? a.title.localeCompare(b.title)
    : sortBy === 'popular' ? (b.borrow_count || 0)-(a.borrow_count || 0) || a.title.localeCompare(b.title)
    : sortBy === 'author' ? a.author.localeCompare(b.author)
    : libraryDate(b.created_at).getTime() - libraryDate(a.created_at).getTime() || b.id - a.id);
  const activeLoans = borrows.filter(loan => loan.status === 'borrowed' && loan.book);
  const borrowedIds = new Set(borrows.map(loan => loan.book_id));
  const borrowedCategories = new Set(borrows.map(loan => loan.book?.category).filter(Boolean));
  const relatedBooks = books.filter(book => book.category && borrowedCategories.has(book.category) && !borrowedIds.has(book.id)).slice(0, 4);
  const showDiscovery = !reviewMode && !searchQuery && selectedCategory === 'All' && selectedLibrary === 'all' && !availableOnly;

  const shelf = (title: string, items: Book[], caption: string) => items.length > 0 && (
    <section aria-label={title} className="space-y-3">
      <h2 className="text-lg font-bold text-white">{title}</h2>
      <p className="text-sm text-gray-400">{caption}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {items.map(book => <Link key={book.id} to={`/books/${book.id}`} className="flex gap-3 p-3 bg-[#111827]/80 border border-gray-800 rounded-xl hover:border-blue-500/50 min-w-0">
          <BookCover book={book} className="w-20 h-28 shrink-0" />
          <div className="min-w-0 self-center"><h3 className="text-sm text-white font-semibold line-clamp-2">{book.title}</h3><p className="text-xs text-gray-400 mt-1">{book.author}</p><p className="text-xs text-blue-400 mt-2">View book →</p></div>
        </Link>)}
      </div>
    </section>
  );

  const handleBorrow = async (bookId: number, title: string) => {
    const book = books.find(item => item.id === bookId);
    if (!book || pendingBook !== null || personalError) return;
    const action = loanAction(book, borrows, reservations);
    if (action.disabled) return;
    setPendingBook(bookId);
    setBorrowSuccess(null);
    setBorrowError(null);
    try {
      await api.post('/reservations/', { book_id: bookId });
      setBorrowSuccess(`Reserved "${title}". View its status in My Library.`);
      // Refresh inventory
      await fetchBooks();
    } catch (err: any) {
      setBorrowError(libraryError(err, 'Unable to complete this request. Please try again.'));
    } finally {
      setPendingBook(null);
    }
  };

  return (
    <div className="max-w-[1600px] mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-blue-400" /> {reviewMode ? 'Book Reviews' : 'Discover'}
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {reviewMode ? 'Choose a book to read reader reviews or share your own.' : 'Explore your library’s books, find your next subject, and manage your reading.'}
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            aria-label="Search catalog"
            value={searchQuery}
            onChange={(e) => updateFilter('search', e.target.value)}
            placeholder="Search by title, author, or ISBN..."
            className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {!isLoading && !loadError && showDiscovery && <>
        {!personalError && shelf('Your borrowed books', activeLoans.map(loan => loan.book!).slice(0, 4), 'Pick up a current loan or check its details in My Library.')}
        {!personalError && shelf('Based on your borrowing', relatedBooks, 'More books in categories you have borrowed.')}
        {shelf('Most borrowed', [...books].filter(b=>(b.borrow_count || 0)>0).sort((a,b)=>(b.borrow_count || 0)-(a.borrow_count || 0)).slice(0,4), 'Ranked by recorded borrowing history across the catalog.')}
        {shelf('Newly added', [...books].sort((a, b) => libraryDate(b.created_at).getTime() - libraryDate(a.created_at).getTime() || b.id - a.id).slice(0, 4), 'Recent additions to the library catalog.')}
        <Link to="/resources" className="inline-flex text-sm text-blue-400 hover:underline">Explore the Digital Library →</Link>
      </>}

      {(loadError || personalError) && <div role="alert" className="p-4 border border-amber-500/30 rounded-xl text-amber-300 text-sm">{loadError || personalError} <button onClick={fetchBooks} className="underline ml-2">Retry</button></div>}

      {/* Alerts */}
      {borrowSuccess && (
        <div role="status" className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2.5">
          <CheckCircle className="w-5 h-5 shrink-0" />
          <span>{borrowSuccess}</span>
        </div>
      )}

      {borrowError && (
        <div role="alert" className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2.5">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{borrowError}</span>
        </div>
      )}

      {/* Category Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => updateFilter('category', cat === 'All' ? '' : cat)}
            aria-pressed={selectedCategory === cat}
            className={`px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
              selectedCategory === cat
                ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]'
                : 'bg-[#172033]/80 text-gray-400 hover:text-white hover:bg-gray-800 border border-gray-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-300">
        <h2 className="font-semibold text-white mr-auto">All books {!isLoading && !loadError && `(${filteredBooks.length})`}</h2>
        <select aria-label="Library" value={selectedLibrary} onChange={e => updateFilter('library', e.target.value === 'all' ? '' : e.target.value)} className="max-w-full bg-[#172033] border border-gray-700 rounded-lg p-2">
          <option value="all">All libraries</option>{libraries.map(library => <option key={library.id} value={library.id}>{library.name}</option>)}
        </select>
        <label className="flex items-center gap-2"><input type="checkbox" checked={availableOnly} onChange={e => updateFilter('available', e.target.checked ? 'true' : '')} />Available now</label>
        <select aria-label="Sort books" value={sortBy} onChange={e => updateFilter('sort', e.target.value)} className="bg-[#172033] border border-gray-700 rounded-lg p-2"><option value="newest">Newest additions</option><option value="popular">Most borrowed</option><option value="title">Title A–Z</option><option value="author">Author A–Z</option></select>
        <button onClick={() => setParams({})} className="text-blue-400 underline">Clear filters</button>
      </div>

      {/* Book Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-80 bg-[#111827]/40 rounded-2xl animate-pulse border border-gray-800" />
          ))}
        </div>
      ) : loadError ? null : filteredBooks.length === 0 ? (
        <div className="text-center py-16 bg-[#111827]/40 border border-gray-800/60 rounded-2xl">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-white">No books found</h3>
          <p className="text-gray-400 text-sm mt-1">Try adjusting your search query or selected category filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filteredBooks.map((book) => (
            <div
              key={book.id}
              data-book-id={book.id}
              className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4 flex flex-col justify-between hover:border-blue-500/40 transition duration-200 group"
            >
              <div>
                {/* Book Cover */}
                <div className="w-full h-56 rounded-xl overflow-hidden bg-gray-900 mb-3.5 relative flex items-center justify-center">
                  <BookCover book={book} className="w-full h-full" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-60" />
                  {book.rack && (
                    <span className="absolute top-2.5 right-2.5 text-[10px] bg-black/70 backdrop-blur-md text-gray-300 border border-gray-700/60 px-2 py-0.5 rounded-md font-medium">
                      Rack {book.rack}{book.shelf ? ` · Shelf ${book.shelf}` : ''}
                    </span>
                  )}
                </div>

                {/* Info */}
                <h3 className="text-white font-bold text-base line-clamp-1 group-hover:text-blue-400 transition">
                  {book.title}
                </h3>
                <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{book.author}</p>

                {book.category && (
                  <span className="inline-block mt-2 text-[10px] px-2 py-0.5 rounded-md bg-blue-900/30 text-blue-300 border border-blue-700/30 font-medium">
                    {book.category}
                  </span>
                )}

                <p className="text-xs text-gray-400 line-clamp-2 mt-2 leading-relaxed">
                  {book.description || 'No description available.'}
                </p>
              </div>

              {/* Action area */}
              <div className="mt-4 pt-3 border-t border-gray-800/80">
                <div className="flex items-center justify-between text-xs mb-3">
                  <span className={`flex items-center gap-1.5 font-medium ${
                    book.available_copies > 0 ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      book.available_copies > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                    }`} />
                    {book.available_copies > 0 ? `Available (${book.available_copies})` : 'No copies currently available'}
                  </span>
                  {book.publication_year && (
                    <span className="text-gray-500 text-[11px]">{book.publication_year}</span>
                  )}
                </div>

                  <p className="text-xs text-gray-400">{book.borrow_count || 0} recorded loans · {book.review_count ? `${book.average_rating}/5 (${book.review_count} reviews)` : 'No ratings yet'} · {book.library_name || 'Library not assigned'}</p>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <Link
                    to={`/books/${book.id}${reviewMode ? '#review-section' : ''}`}
                    className="bg-[#1e293b] hover:bg-gray-700 text-gray-200 text-xs font-semibold py-2 rounded-xl transition text-center"
                  >
                    {reviewMode ? 'Read reviews' : 'Details'}
                  </Link>

                  <button
                    onClick={() => handleBorrow(book.id, book.title)}
                    aria-label={`${loanAction(book, borrows, reservations).label}: ${book.title}`}
                    disabled={pendingBook !== null || !!personalError || loanAction(book, borrows, reservations).disabled}
                    className={`text-xs font-semibold py-2 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed ${
                      !loanAction(book, borrows, reservations).disabled
                        ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-[0_0_10px_rgba(37,99,235,0.3)]'
                        : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                    }`}
                  >
                    {pendingBook === book.id ? 'Saving…' : loanAction(book, borrows, reservations).label}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
