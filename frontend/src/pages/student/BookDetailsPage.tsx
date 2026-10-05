import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import api from '../../services/api';
import type { Book, Review, BorrowRecord, Reservation, DigitalResource, Library } from '../../types';
import BookCover from '../../components/BookCover';
import { useAuth } from '../../context/AuthContext';
import { libraryError, libraryDate, loanAction } from '../../utils/library';
import {
  BookOpen, Star, ArrowLeft, CheckCircle, AlertCircle, Clock,
  MapPin, Calendar, Tag, MessageSquare, Send
} from 'lucide-react';

export default function BookDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const location = useLocation();
  const requestVersion = useRef(0);

  const [book, setBook] = useState<Book | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [ratingSummary, setRatingSummary] = useState({ average_rating: 0, total_reviews: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reviewLoadError, setReviewLoadError] = useState(false);
  const [supportError, setSupportError] = useState(false);
  const [canAct, setCanAct] = useState(false);
  const [borrows, setBorrows] = useState<BorrowRecord[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [catalog, setCatalog] = useState<Book[]>([]);
  const [resources, setResources] = useState<DigitalResource[]>([]);
  const [libraries, setLibraries] = useState<Library[]>([]);

  // Review Form
  const [userRating, setUserRating] = useState(5);
  const [userComment, setUserComment] = useState('');
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Borrow/Reserve Feedback
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isBorrowing, setIsBorrowing] = useState(false);

  useEffect(() => {
    setActionMessage(null);
    setReviewFeedback(null);
    if (id) {
      fetchBookDetails(id);
    }
    return () => { requestVersion.current += 1; };
  }, [id]);

  useEffect(() => {
    if (!isLoading && book && location.hash === '#review-section') document.getElementById('review-section')?.scrollIntoView({ block: 'start' });
  }, [isLoading, book?.id, location.hash]);

  const fetchBookDetails = async (bookId: string) => {
    const version = ++requestVersion.current;
    setIsLoading(true);
    setLoadError(null);
    setCanAct(false);
    try {
      const [bookRes, reviewsRes, ratingRes, catalogRes, resourcesRes, loansRes, holdsRes, librariesRes] = await Promise.allSettled([
        api.get(`/books/${bookId}`),
        api.get(`/reviews/book/${bookId}`),
        api.get(`/reviews/book/${bookId}/rating`),
        api.get<Book[]>('/books/'), api.get<DigitalResource[]>('/digital-resources/'),
        api.get<BorrowRecord[]>('/borrows/my'), api.get<Reservation[]>('/reservations/my'), api.get<Library[]>('/libraries/'),
      ]);
      if (version !== requestVersion.current) return;
      if (bookRes.status === 'rejected') throw bookRes.reason;
      setBook(bookRes.value.data);
      const loadedReviews: Review[] = reviewsRes.status === 'fulfilled' ? reviewsRes.value.data : [];
      setReviews(loadedReviews);
      setReviewLoadError(reviewsRes.status === 'rejected' || ratingRes.status === 'rejected');
      setRatingSummary(ratingRes.status === 'fulfilled' ? ratingRes.value.data : { average_rating: 0, total_reviews: 0 });
      const mine = loadedReviews.find(review => review.user_id === user?.id);
      setUserRating(mine?.rating ?? 5);
      setUserComment(mine?.comment ?? '');
      setCatalog(catalogRes.status === 'fulfilled' ? catalogRes.value.data : []);
      setResources(resourcesRes.status === 'fulfilled' ? resourcesRes.value.data : []);
      setLibraries(librariesRes.status === 'fulfilled' ? librariesRes.value.data : []);
      setBorrows(loansRes.status === 'fulfilled' ? loansRes.value.data : []);
      setReservations(holdsRes.status === 'fulfilled' ? holdsRes.value.data : []);
      setCanAct(loansRes.status === 'fulfilled' && holdsRes.status === 'fulfilled');
      setSupportError([catalogRes, resourcesRes, loansRes, holdsRes, librariesRes].some(result => result.status === 'rejected'));
    } catch (err) {
      if (version !== requestVersion.current) return;
      setBook(null);
      setLoadError(libraryError(err, 'Unable to load this book. Please try again.'));
    } finally {
      if (version === requestVersion.current) setIsLoading(false);
    }
  };

  const handleBorrowOrReserve = async () => {
    if (!book || isBorrowing || !canAct) return;
    const action = loanAction(book, borrows, reservations);
    if (action.disabled) return;
    setActionMessage(null);
    setIsBorrowing(true);

    try {
      await api.post('/reservations/', { book_id: book.id });
      setActionMessage({type:'success',text:`Reserved "${book.title}". Check My Library for pickup status.`});
      // Refresh book data
      if (id) await fetchBookDetails(id);
    } catch (err: any) {
      setActionMessage({
        type: 'error',
        text: libraryError(err, 'Action failed. Please try again.'),
      });
    } finally {
      setIsBorrowing(false);
    }
  };

  const canReview=canAct && borrows.some(loan=>loan.book_id===book?.id && ['borrowed','returned'].includes(loan.status));
  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!book || isSubmittingReview || !canReview) return;

    const trimmedComment = userComment.trim();
    if (!trimmedComment) {
      setReviewFeedback({ type: 'error', text: 'Review comment cannot be empty. Please share your thoughts.' });
      return;
    }
    if (userRating < 1 || userRating > 5) {
      setReviewFeedback({ type: 'error', text: 'Rating must be between 1 and 5 stars.' });
      return;
    }

    setIsSubmittingReview(true);
    setReviewFeedback(null);

    try {
      await api.post('/reviews/', {
        book_id: book.id,
        rating: userRating,
        comment: trimmedComment,
      });
      setUserComment('');
      setReviewFeedback({ type: 'success', text: 'Your review has been successfully published!' });

      // Instantly update reviews list and rating summary without full page reload
      const [reviewsRes, ratingRes] = await Promise.all([
        api.get(`/reviews/book/${book.id}`),
        api.get(`/reviews/book/${book.id}/rating`),
      ]);
      setReviews(reviewsRes.data || []);
      setRatingSummary(ratingRes.data || { average_rating: 0, total_reviews: 0 });
    } catch (err: any) {
      setReviewFeedback({
        type: 'error',
        text: libraryError(err, 'Failed to submit review. Please try again.'),
      });
    } finally {
      setIsSubmittingReview(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-12 flex justify-center">
        <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!book) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <h2 className="text-xl font-bold text-white mb-2">Book unavailable</h2>
        <p role="alert" className="text-gray-400 mb-4">{loadError || 'This book could not be found.'}</p>
        <button onClick={() => id && fetchBookDetails(id)} className="text-blue-400 underline mr-4">Retry</button>
        <Link to="/books" className="text-blue-400 hover:underline">
          Return to Catalog
        </Link>
      </div>
    );
  }

  const action = loanAction(book, borrows, reservations);
  const library = libraries.find(item => item.id === book.library_id);
  const similar = catalog.filter(item => item.id !== book.id && ((book.category && item.category === book.category) || item.author === book.author)).slice(0, 4);
  const normalize = (value?: string) => value?.trim().toLowerCase() || '';
  const normalizeIsbn = (value?: string) => value?.replace(/[-\s]/g, '').toUpperCase() || '';
  const editions = resources.filter(item => (book.isbn && normalizeIsbn(item.isbn) === normalizeIsbn(book.isbn)) || (normalize(item.title) === normalize(book.title) && normalize(item.author) === normalize(book.author)));
  const editionUrl = (item: DigitalResource) => {
    try {
      const value = item.file_url || item.external_url;
      if (!value) return undefined;
      const url = new URL(value, new URL(api.defaults.baseURL || '/', window.location.origin));
      return ['http:', 'https:'].includes(url.protocol) ? url.href : undefined;
    } catch { return undefined; }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Back button */}
      <Link
        to="/books"
        className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Discover
      </Link>

      {(supportError || reviewLoadError) && <div role="alert" className="text-amber-300 text-sm">Some library information could not be loaded. <button className="underline" onClick={() => id && fetchBookDetails(id)}>Retry</button></div>}

      {/* Action banner message */}
      {actionMessage && (
        <div
          role={actionMessage.type === 'error' ? 'alert' : 'status'}
          className={`p-4 rounded-xl text-sm flex items-center gap-2.5 ${
            actionMessage.type === 'success'
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-400'
          }`}
        >
          {actionMessage.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Main Book Info Card */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 md:p-8 grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Cover Column */}
        <div className="md:col-span-4 flex flex-col items-center">
          <BookCover book={book} className="w-full max-w-[280px] h-96 shadow-2xl" />

          <div className="w-full max-w-[280px] mt-4">
            <button
              onClick={handleBorrowOrReserve}
              disabled={isBorrowing || !canAct || action.disabled}
              className={`w-full font-bold py-3.5 rounded-xl transition flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${
                book.available_copies > 0
                  ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-600/30'
                  : 'bg-amber-600 hover:bg-amber-700 text-white shadow-amber-600/30'
              }`}
            >
              {isBorrowing ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : <><BookOpen className="w-5 h-5" />{canAct ? action.label : 'Loan status unavailable'}</>}
            </button>
            <Link to="/my-books" className="block text-center text-blue-400 text-sm mt-3 hover:underline">View My Library</Link>
            {editions.filter(item => editionUrl(item)).map(item => <a key={item.id} href={editionUrl(item)} target="_blank" rel="noopener noreferrer" className="block text-center text-blue-300 text-sm mt-3 border border-blue-500/30 rounded-xl p-3">Read digital edition · {item.provider}</a>)}

            {/* Review Action Trigger Button */}
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('review-section');
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  const textarea = el.querySelector('textarea');
                  if (textarea) textarea.focus();
                }
              }}
              className="w-full mt-2.5 font-semibold py-2.5 px-4 rounded-xl transition flex items-center justify-center gap-2 bg-[#172033] hover:bg-blue-600/20 text-blue-400 hover:text-blue-300 border border-blue-500/30 text-xs shadow-md"
            >
              <MessageSquare className="w-4 h-4" /> Review This Book
            </button>
          </div>
        </div>

        {/* Details Column */}
        <div className="md:col-span-8 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {book.category && (
                <span className="text-xs px-2.5 py-1 rounded-md bg-blue-900/30 text-blue-300 border border-blue-700/30 font-semibold">
                  {book.category}
                </span>
              )}
              <span
                className={`text-xs px-2.5 py-1 rounded-md font-semibold ${
                  book.available_copies > 0
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}
              >
                {book.available_copies > 0 ? `${book.available_copies} Copies Available` : 'Currently Checked Out'}
              </span>
            </div>

            <h1 className="text-3xl font-extrabold text-white mt-1">{book.title}</h1>
            <p className="text-base text-gray-300 font-medium mt-1">by {book.author}</p>

            {/* Rating Stars */}
            <div className="flex items-center gap-2 mt-3">
              <div className="flex items-center text-amber-400">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-4 h-4 ${
                      !reviewLoadError && i < Math.floor(ratingSummary.average_rating)
                        ? 'fill-amber-400 text-amber-400'
                        : 'text-gray-600'
                    }`}
                  />
                ))}
              </div>
              <span className="text-sm font-bold text-white">{reviewLoadError ? 'Ratings unavailable' : ratingSummary.total_reviews > 0 ? ratingSummary.average_rating.toFixed(1) : 'Not rated yet'}</span>
              {!reviewLoadError && <span className="text-xs text-gray-500">({ratingSummary.total_reviews} reviews)</span>}
            </div>

            {/* Shelf / Metadata Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">
              <div className="bg-[#172033] p-3 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-blue-400" /> Physical Rack
                </span>
                <p className="text-sm font-bold text-white mt-0.5">{[book.rack && `Rack ${book.rack}`, book.shelf && `Shelf ${book.shelf}`].filter(Boolean).join(' · ') || 'Not specified'}</p>
              </div>

              <div className="bg-[#172033] p-3 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 flex items-center gap-1">
                  <Tag className="w-3.5 h-3.5 text-blue-400" /> ISBN
                </span>
                <p className="text-xs font-bold text-white mt-1 truncate">{book.isbn || 'N/A'}</p>
              </div>

              <div className="bg-[#172033] p-3 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-blue-400" /> Year
                </span>
                <p className="text-sm font-bold text-white mt-0.5">{book.publication_year ?? 'Not specified'}</p>
              </div>

              <div className="bg-[#172033] p-3 rounded-xl border border-gray-800">
                <span className="text-[11px] text-gray-400 flex items-center gap-1">
                  <BookOpen className="w-3.5 h-3.5 text-blue-400" /> Total Stock
                </span>
                <p className="text-sm font-bold text-white mt-0.5">{book.total_copies} Copies</p>
              </div>
            </div>
            <p className="text-sm text-gray-400 mb-4">Library: {library?.name || 'Not specified'}{library?.campus ? ` · ${library.campus}` : ''}</p>

            {/* Description */}
            <div>
              <h3 className="text-sm font-bold text-white mb-2">Book Synopsis & Details</h3>
              <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-line bg-[#172033]/40 p-4 rounded-xl border border-gray-800/80">
                {book.description || 'No detailed description available for this catalog entry.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Reviews & Ratings Section */}
      <div id="review-section" className="grid grid-cols-1 md:grid-cols-12 gap-8 scroll-mt-24">
        {/* Review Form */}
        <div className="md:col-span-5 bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2 mb-2">
            <MessageSquare className="w-5 h-5 text-blue-400" /> Write a Review
          </h2>
          <p className="text-xs text-gray-400 mb-4">Help other readers choose their next book. Posting again updates your existing review.</p>

          {reviewFeedback && (
            <div
              role={reviewFeedback.type === 'error' ? 'alert' : 'status'}
              className={`mb-4 p-3 rounded-xl text-xs flex items-center gap-2 ${
                reviewFeedback.type === 'success'
                  ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-400'
                  : 'bg-red-500/15 border border-red-500/30 text-red-400'
              }`}
            >
              {reviewFeedback.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
              <span>{reviewFeedback.text}</span>
            </div>
          )}

          {!canReview && <p className="text-sm text-amber-300 mb-4">Reviews require a recorded loan for this book. Existing reviews remain visible.</p>}
          {canReview && <form onSubmit={handleReviewSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-2">Your Rating</label>
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    type="button"
                    key={star}
                    aria-label={`Rate ${star} ${star === 1 ? 'star' : 'stars'}`}
                    aria-pressed={userRating === star}
                    onClick={() => setUserRating(star)}
                    className="p-1 hover:scale-110 transition"
                  >
                    <Star
                      className={`w-6 h-6 ${
                        star <= userRating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'
                      }`}
                    />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="review-comment" className="block text-xs font-semibold text-gray-300 mb-2">Your Comments</label>
              <textarea
                id="review-comment"
                value={userComment}
                onChange={(e) => setUserComment(e.target.value)}
                placeholder="What did you learn from this book? Was it beginner friendly?"
                rows={4}
                required
                className="w-full bg-[#172033] border border-gray-700/50 rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmittingReview}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl text-xs transition flex items-center justify-center gap-2"
            >
              {isSubmittingReview ? 'Submitting...' : 'Post Review'}
            </button>
          </form>}
        </div>

        {/* Existing Reviews List */}
        <div className="md:col-span-7 bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6">
          <h2 className="text-lg font-bold text-white mb-4">Student Reviews ({reviews.length})</h2>

          {reviewLoadError ? <p className="text-gray-400 text-sm">Reviews could not be loaded. Please retry above.</p> : reviews.length === 0 ? (
            <div className="text-center py-10">
              <Star className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="text-xs text-gray-400">No reviews yet. Be the first to review this book!</p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[420px] overflow-y-auto pr-2">
              {reviews.map((r) => (
                <div key={r.id} className="bg-[#172033]/60 p-4 rounded-xl border border-gray-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{r.user?.name || 'Student'}</span>
                    <div className="flex items-center text-amber-400 gap-0.5">
                      {[...Array(r.rating)].map((_, i) => (
                        <Star key={i} className="w-3 h-3 fill-amber-400" />
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">{r.comment}</p>
                  <p className="text-[10px] text-gray-500">
                    {new Date(r.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {similar.length > 0 && <section aria-label="Similar books"><h2 className="text-lg text-white font-bold mb-4">Similar books</h2><div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">{similar.map(item => <Link key={item.id} to={`/books/${item.id}`} className="bg-[#111827]/80 border border-gray-800 rounded-xl p-4 hover:border-blue-500/40"><BookCover book={item} className="h-44 mb-3" /><h3 className="text-white text-sm font-semibold">{item.title}</h3><p className="text-xs text-gray-400 mt-1">{item.author}</p></Link>)}</div></section>}
    </div>
  );
}
