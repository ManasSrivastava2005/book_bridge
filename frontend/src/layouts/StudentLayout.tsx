import { useState, useMemo, useEffect } from 'react';
import { Link, useLocation, Outlet, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Home, BookOpen, Layers, Sparkles, Route, Star, MessageSquare,
  Target, Trophy, Settings, Bell, LogOut, Menu, X, ChevronDown,
  QrCode, Shield, PlusCircle, Globe, FileText, FileCheck, Landmark,
  Search
} from 'lucide-react';

/* ───────────────────── Logo Component ─────────────────── */
/* 3D dual-page glowing open book matching 4th reference design */
const BookBridgeLogo = () => (
  <svg
    width="24"
    height="22"
    viewBox="0 0 24 22"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="shrink-0 drop-shadow-[0_0_8px_rgba(56,189,248,0.5)]"
  >
    <path
      d="M12 4.5C9.8 3 5.5 3.2 1.5 4.5V17.5C5.5 16 9.8 15.8 12 17.5V4.5Z"
      fill="url(#bb-left-page)"
    />
    <path
      d="M12 4.5C14.2 3 18.5 3.2 22.5 4.5V17.5C18.5 16 14.2 15.8 12 17.5V4.5Z"
      fill="url(#bb-right-page)"
    />
    <path d="M12 4.5V17.5" stroke="#93c5fd" strokeWidth="0.8" />
    <path d="M1.5 17.5C5.5 16 9.8 15.8 12 17.5C14.2 15.8 18.5 16 22.5 17.5" stroke="#60a5fa" strokeWidth="1" />
    <defs>
      <linearGradient id="bb-left-page" x1="1.5" y1="3" x2="12" y2="18" gradientUnits="userSpaceOnUse">
        <stop stopColor="#38bdf8" />
        <stop offset="1" stopColor="#1d4ed8" />
      </linearGradient>
      <linearGradient id="bb-right-page" x1="22.5" y1="3" x2="12" y2="18" gradientUnits="userSpaceOnUse">
        <stop stopColor="#60a5fa" />
        <stop offset="1" stopColor="#2563eb" />
      </linearGradient>
    </defs>
  </svg>
);

/* ───────────────── Navigation Configuration ───────────── */
const primaryStudentNavItems = [
  { path: '/dashboard', label: 'Home', icon: Home },
  { path: '/books', label: 'Discover', icon: BookOpen },
  { path: '/my-books', label: 'My Library', icon: Layers },
  { path: '/ai', label: 'AI Assistant', icon: Sparkles },
  { path: '/study-together', label: 'Study Together', icon: MessageSquare },
  { path: '/curriculum', label: 'My Curriculum', icon: BookOpen },
  { path: '/learning-path', label: 'Learning Path', icon: Route },
  { path: '/recommendations', label: 'Recommendations', icon: Star },
  { path: '/books?view=reviews', label: 'Reviews', icon: MessageSquare },
  { path: '/quizzes', label: 'Quizzes', icon: Target },
  { path: '/leaderboard', label: 'Leaderboard', icon: Trophy },
];

const secondaryStudentNavItems = [
  { path: '/resources', label: 'Digital Library', icon: Landmark },
  { path: '/notes', label: 'Notes Library', icon: FileText },
  { path: '/question-banks', label: 'Question Banks', icon: FileCheck },
  { path: '/scan', label: 'Scan & Locate', icon: QrCode },
  { path: '/settings', label: 'Settings', icon: Settings },
];

const librarianNavItems = [
  { path: '/admin/dashboard', label: 'Librarian Hub', icon: Shield },
  { path: '/admin/books', label: 'Manage Catalog', icon: PlusCircle },
  { path: '/admin/circulation', label: 'Circulation', icon: Layers },
  { path: '/admin/study-moderation', label: 'Study Moderation', icon: Shield },
  { path: '/admin/resources', label: 'Manage E-Books', icon: Globe },
];

/* ─────────────── Daily Motivational Quotes ─────────────── */
const dailyQuotes = [
  "A little progress each day adds up to big results.",
  "Today a reader, tomorrow a leader.",
  "An investment in knowledge pays the best interest.",
  "The expert in anything was once a beginner.",
  "Small disciplines repeated with consistency lead to great achievements.",
  "Reading is to the mind what exercise is to the body.",
  "Knowledge has a beginning but no end.",
  "The beautiful thing about learning is that no one can take it away.",
  "Live as if you were to die tomorrow. Learn as if you were to live forever.",
  "The more that you read, the more things you will know.",
];

export default function StudentLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [unread,setUnread]=useState(0);
  useEffect(()=>{
    let active=true;let running=false;
    const check=async()=>{if(running || document.hidden)return;running=true;try{const response=await api.get('/notifications/unread-count');if(active)setUnread(response.data.count);}catch{/* Inbox reports errors when opened. */}finally{running=false;}};
    void check();const timer=window.setInterval(()=>void check(),60000);
    window.addEventListener('notifications-updated',check);
    return()=>{active=false;window.clearInterval(timer);window.removeEventListener('notifications-updated',check);};
  },[user?.id]);
  const [globalSearch, setGlobalSearch] = useState('');

  const isActive = (path: string) => {
    if (path.includes('?')) return `${location.pathname}${location.search}` === path;
    if (path === '/books' && location.search.includes('view=reviews')) return false;
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  // Compute daily quote uniquely per calendar date
  const todaysQuote = useMemo(() => {
    const today = new Date();
    const dayOfYear = Math.floor(
      (today.getTime() - new Date(today.getFullYear(), 0, 0).getTime()) / (1000 * 60 * 60 * 24)
    );
    return dailyQuotes[dayOfYear % dailyQuotes.length];
  }, []);

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!globalSearch.trim()) return;
    navigate(`/books?search=${encodeURIComponent(globalSearch.trim())}`);
  };

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const avatarUrl = user?.profile_image
    ? user.profile_image.startsWith('http')
      ? user.profile_image
      : `${API_BASE}${user.profile_image}`
    : null;

  return (
    <div className="min-h-screen bg-[#070b16] flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ────────────────── EXACT 4TH REFERENCE SIDEBAR ────────────────── */}
      <aside
        className={`fixed md:relative inset-y-0 left-0 z-50 w-[188px] bg-[#060c1c]/80 backdrop-blur-2xl border-r border-[#15233e]/50 flex flex-col shrink-0 overflow-hidden shadow-2xl transition-transform duration-200 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Subtle Bookshelf & Reading Room Background Texture at the bottom */}
        <div
          className="absolute inset-x-0 bottom-0 h-[340px] bg-cover bg-bottom pointer-events-none opacity-45 mix-blend-screen"
          style={{
            backgroundImage: 'url(/sidebar-clean-bookshelf.png)',
            maskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 50%, rgba(0,0,0,0) 100%)',
            WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 50%, rgba(0,0,0,0) 100%)',
          }}
        />

        {/* Dark Navy Glass Ambient Sheen Layer */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#060c1c]/95 via-[#060c1c]/75 to-[#050a17]/85 pointer-events-none" />

        {/* 1. Header: Glowing Logo & Branding */}
        <div className="relative z-10 px-3.5 pt-5 pb-4 flex items-center gap-2.5">
          <BookBridgeLogo />
          <div className="flex flex-col min-w-0">
            <h1 className="text-white font-bold text-[14.5px] leading-tight tracking-tight font-sans">
              Book Bridge
            </h1>
            <p className="text-[#8497b0] text-[9.5px] tracking-wide mt-0.5 font-normal">
              Read &nbsp;•&nbsp; Learn &nbsp;•&nbsp; Grow
            </p>
          </div>
          <button
            aria-label="Close navigation"
            className="md:hidden ml-auto text-gray-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 2. Main Navigation Items */}
        <nav className="relative z-10 flex-1 px-2 py-1 space-y-0.5 overflow-y-auto">
          {primaryStudentNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={active ? 'page' : undefined}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl text-[12.5px] font-medium transition-all group ${
                  active
                    ? 'bg-[#10274f] text-[#60a5fa] border border-[#2563eb]/45 shadow-[0_0_14px_rgba(37,99,235,0.22)]'
                    : 'text-[#94a3b8] hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    active
                      ? 'text-[#60a5fa]'
                      : 'text-[#94a3b8] group-hover:text-white'
                  }`}
                  strokeWidth={1.75}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}

          {/* Subtle separator line before resources and settings */}
          <div className="pt-2 pb-1">
            <div className="h-[1px] bg-gray-800/60 mx-2" />
          </div>

          {secondaryStudentNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl text-[12.5px] font-medium transition-all group ${
                  active
                    ? 'bg-[#10274f] text-[#60a5fa] border border-[#2563eb]/45 shadow-[0_0_14px_rgba(37,99,235,0.22)]'
                    : 'text-[#94a3b8] hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    active
                      ? 'text-[#60a5fa]'
                      : 'text-[#94a3b8] group-hover:text-white'
                  }`}
                  strokeWidth={1.75}
                />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}

          {/* Librarian Portal (when authenticated as librarian) */}
          {(user?.role === 'librarian' || user?.role === 'admin') && (
            <div className="pt-2 mt-2 border-t border-gray-800/50">
              <span className="px-3 text-[9px] font-bold uppercase tracking-wider text-amber-400/80 block mb-1">
                Staff
              </span>
              {librarianNavItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-xl text-[12.5px] font-medium transition-all ${
                      active
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        : 'text-gray-400 hover:bg-white/[0.04] hover:text-white'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0 text-amber-400" strokeWidth={1.75} />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </nav>

        {/* 3. Bottom Atmospheric Daily Quote Card */}
        <div className="relative z-10 px-3.5 pb-5 pt-2 mt-auto">
          <p className="text-[11px] text-[#cbd5e1]/90 italic leading-relaxed font-sans drop-shadow-sm">
            "{todaysQuote}"
          </p>
          {/* Cyan/Blue Accent Underline matching target design */}
          <div className="w-7 h-[2px] bg-[#60a5fa] rounded-full mt-2.5 shadow-[0_0_6px_rgba(96,165,250,0.5)]" />
        </div>
      </aside>

      {/* ────────────────── MAIN CONTENT & TOPBAR ────────────────── */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Top Bar */}
        <header className="sticky top-0 z-30 bg-[#0f1320]/90 backdrop-blur-xl border-b border-gray-800/60 px-4 lg:px-6 py-3">
          <div className="flex items-center gap-4">
            <button aria-label="Open navigation" className="md:hidden text-gray-400 hover:text-white" onClick={() => setSidebarOpen(true)}>
              <Menu className="w-6 h-6" />
            </button>

            {/* Search Bar */}
            <form onSubmit={handleGlobalSearch} className="flex-1 max-w-xl">
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  aria-label="Search library catalog"
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  placeholder="Search books by title, author, or ISBN..."
                  className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-10 pr-12 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                />
                <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded border border-gray-700 font-mono">
                  /
                </kbd>
              </div>
            </form>

            {/* Right side */}
            <div className="flex items-center gap-3 ml-auto">
              <Link to="/notifications" aria-label="Notifications" className="relative p-2 text-gray-400 hover:text-white transition">
                <Bell className="w-5 h-5" />{unread>0 && <span aria-label={`${unread} unread notifications`} className="absolute -top-1 -right-1 rounded-full bg-blue-600 px-1 text-[10px] text-white">{unread>99?'99+':unread}</span>}
              </Link>

              {/* User Profile */}
              <div className="relative">
                <button
                  onClick={() => setProfileOpen(!profileOpen)}
                  className="flex items-center gap-2.5 hover:bg-white/5 rounded-xl px-2 py-1.5 transition"
                >
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt={user?.name}
                      className="w-8 h-8 rounded-full object-cover border border-blue-500/40"
                    />
                  ) : (
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold border border-blue-400/30">
                      {user?.name?.charAt(0) || 'M'}
                    </div>
                  )}
                  <div className="hidden md:block text-left">
                    <p className="text-xs text-white font-semibold leading-tight">{user?.name || 'Student'}</p>
                    <p className="text-[10px] text-gray-400">
                      {user?.role === 'student' ? (user.branch ? `Student • ${user.branch.split(' ')[0]}` : 'Student') : user?.role === 'admin' ? 'Administrator' : 'Librarian'}
                    </p>
                  </div>
                  <ChevronDown className="w-3.5 h-3.5 text-gray-400 hidden md:block" />
                </button>

                {profileOpen && (
                  <div className="absolute right-0 mt-2 w-52 bg-[#172033] border border-gray-700/60 rounded-xl shadow-2xl py-1 z-50">
                    <div className="px-4 py-2 border-b border-gray-800">
                      <p className="text-xs font-bold text-white truncate">{user?.name}</p>
                      <p className="text-[10px] text-gray-400 truncate">{user?.email}</p>
                    </div>
                    <Link
                      to="/settings"
                      onClick={() => setProfileOpen(false)}
                      className="block px-4 py-2 text-xs text-gray-300 hover:bg-white/5 hover:text-white"
                    >
                      Profile & Settings
                    </Link>
                    <Link
                      to="/my-books"
                      onClick={() => setProfileOpen(false)}
                      className="block px-4 py-2 text-xs text-gray-300 hover:bg-white/5 hover:text-white"
                    >
                      My Library
                    </Link>
                    <hr className="border-gray-800 my-1" />
                    <button
                      onClick={() => {
                        setProfileOpen(false);
                        logout();
                      }}
                      className="w-full text-left px-4 py-2 text-xs text-red-400 hover:bg-white/5 flex items-center gap-2"
                    >
                      <LogOut className="w-3.5 h-3.5" /> Logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
