import StudyRoomsSummary from '../../components/StudyRoomsSummary';
import StudentProgress from '../../components/StudentProgress';
import RecommendationsPage from './RecommendationsPage';
import LearningPathPage from './LearningPathPage';
import BadgeCollection from '../../components/BadgeCollection';
import ReaderLevelCard from '../../components/ReaderLevelCard';
import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import {
  Flame, BookOpen, Award, Star, CheckCircle2, Circle, Lock, Send,
  Bot, Clock, ChevronRight, Sparkles, BookMarked, Target, TrendingUp,
  Layers, ArrowRight, Compass, Shield, MoreVertical
} from 'lucide-react';

/* ───────────────────────── Types ───────────────────────── */
interface BookItem {
  id: number;
  title: string;
  author: string;
  category?: string;
  rating: number;
  reviewsCount: number;
  tags: string[];
  copiesAvailable: number;
  coverImage: string;
}

/* Circular progress ring component */
const CircularProgress = ({ value, max, size = 44, strokeWidth = 3, color = '#3b82f6', children }: {
  value: number; max: number; size?: number; strokeWidth?: number; color?: string; children?: React.ReactNode;
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(value / max, 1);
  const dashOffset = circumference * (1 - progress);

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1e293b" strokeWidth={strokeWidth} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          stroke={color} strokeWidth={strokeWidth} fill="none"
          strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashOffset}
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
};

/* ───────────────────── Main Component ─────────────────── */
export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  /* ── State ── */
  const [summary, setSummary] = useState({
    reader_level: 1,
    xp: 0,
    xp_required: 200,
    reading_streak: 0,
    books_read: 0,
    badges_unlocked: 0,
    active_borrows: 0,
  });

  const [missions, setMissions] = useState<{id:string;title:string;xp:number;completed:boolean}[]>([]);

  const [recentActivity, setRecentActivity] = useState<{type:string;description:string;timestamp:string;color:string}[]>([]);

  /* AI Widget */
  const [aiInput, setAiInput] = useState('');
  const [aiResponses, setAiResponses] = useState<{ query: string; answer: string }[]>([]);
  const [isAiLoading, setIsAiLoading] = useState(false);

  /* Dynamic Greeting and Subtext */
  const getGreetingData = () => {
    const hour = new Date().getHours();
    if (hour < 12) {
      return {
        greeting: 'Good Morning',
        emoji: '☀️',
        subtext: 'Your next chapter is waiting. Keep going!',
      };
    } else if (hour < 17) {
      return {
        greeting: 'Good Afternoon',
        emoji: '🌤️',
        subtext: 'Explore new knowledge and stay curious today.',
      };
    } else {
      return {
        greeting: 'Good Evening',
        emoji: '🌙',
        subtext: 'Relax and unwind with a good read tonight.',
      };
    }
  };

  const { greeting, emoji, subtext } = getGreetingData();
  const studentName = user?.name ? user.name.split(' ')[0] : 'Reader';

  /* ── Fetch real backend data ── */
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const res = await api.get('/dashboard/summary');
        if (res.data) {
          setSummary(prev => ({ ...prev, ...res.data }));
          if (res.data.missions) setMissions(res.data.missions);
        }
      } catch (err) {
        console.log('Dashboard data unavailable', err);
      }

      try {
        const actRes = await api.get('/dashboard/activity');
        if (Array.isArray(actRes.data)) {
          const colorMap: Record<string, string> = { borrow: 'emerald', ai: 'blue', review: 'amber', return: 'purple' };
          setRecentActivity(actRes.data.slice(0, 3).map((a: any) => ({
            type: a.type || 'borrow',
            description: a.description,
            timestamp: a.timestamp,
            color: colorMap[a.type] || 'blue',
          })));
        }
      } catch (err) {
        console.log('Activity unavailable', err);
      }
    };
    fetchDashboardData();
    const refreshMissions = () => { api.get('/dashboard/summary').then(r => { setSummary(prev => ({...prev,...r.data})); setMissions(r.data.missions || []); }).catch(() => {}); };
    const timer = window.setInterval(refreshMissions, 60000);
    window.addEventListener('focus', refreshMissions);
    return () => { clearInterval(timer); window.removeEventListener('focus', refreshMissions); };
  }, []);

  const handlePromptClick = (promptText: string) => setAiInput(promptText);

  const handleAiSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiInput.trim()) return;
    const userQuery = aiInput;
    setAiInput('');
    setIsAiLoading(true);
    try {
      const res = await api.post('/ai/chat', { message: userQuery, query: userQuery });
      const answer = res.data?.response || res.data?.answer || 'I found related materials in our library catalog!';
      setAiResponses(prev => [...prev, { query: userQuery, answer }]);
    } catch {
      const reply = 'The AI Assistant is currently unavailable. Please try again.';
      setAiResponses(prev => [...prev, { query: userQuery, answer: reply }]);
    } finally {
      setIsAiLoading(false);
    }
  };

  /* ── Learning path stages ── */
  const activityIcons: Record<string, any> = { borrow: BookOpen, ai: Bot, review: Star, return: BookMarked };
  const activityColors: Record<string, string> = {
    emerald: 'bg-emerald-500/20 text-emerald-400',
    blue: 'bg-blue-500/20 text-blue-400',
    amber: 'bg-amber-500/20 text-amber-400',
    purple: 'bg-purple-500/20 text-purple-400',
  };

  /* ─────────────────────── RENDER ─────────────────────── */
  return (
    <div className="space-y-5 max-w-[1600px] mx-auto pb-8">
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">

        {/* ════════════ LEFT / CENTER MAIN AREA (8 cols) ════════════ */}
        <div className="xl:col-span-8 space-y-5">

          {/* ▸ 1. WELCOME BANNER — With Custom Scenic Concept Art Background */}
          <div
            className="relative rounded-2xl overflow-hidden border border-blue-900/40 min-h-[175px] md:min-h-[195px] flex flex-col justify-center bg-cover bg-right shadow-2xl"
            style={{
              backgroundImage: 'url(/dashboard-banner.jpg)',
            }}
          >
            {/* Dark gradient overlay on the left for maximum text contrast */}
            <div className="absolute inset-0 bg-gradient-to-r from-[#0a1124] via-[#0a1124]/85 to-transparent pointer-events-none" />
            <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-[#0a1124]/70 to-transparent pointer-events-none" />

            {/* Banner Text Content */}
            <div className="relative z-10 px-6 md:px-8 py-6 max-w-xl">
              <h1 className="text-2xl md:text-3xl font-extrabold text-white flex items-center gap-2.5 tracking-tight drop-shadow-md">
                {greeting}, {studentName}{' '}
                <span className="text-2xl drop-shadow">{emoji}</span>
              </h1>
              <p className="text-blue-100/90 text-sm md:text-base mt-2 font-medium leading-relaxed drop-shadow">
                {subtext}
              </p>
            </div>
          </div>

          {/* ▸ 2. STAT CARDS — 4-column compact grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <ReaderLevelCard />

            {/* Reading Streak with dot indicators */}
            <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
                  <Flame className="w-5 h-5 text-amber-400 fill-amber-400" />
                </div>
                <div>
                  <div className="text-lg font-bold text-white leading-tight">{summary.reading_streak} Days</div>
                  <span className="text-xs text-gray-400">Reading Streak</span>
                </div>
              </div>
              <div className="flex items-center gap-1.5 mt-2.5">
                {[...Array(7)].map((_, i) => (
                  <div
                    key={i}
                    className={`w-2.5 h-2.5 rounded-full transition-colors ${
                      i < summary.reading_streak ? 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.4)]' : 'bg-gray-700'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Books Read */}
            <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <div className="text-lg font-bold text-white leading-tight">{summary.books_read}</div>
                <div className="text-xs text-gray-400">Books Read</div>
                <div className="text-[10px] text-gray-500">This Semester</div>
              </div>
            </div>

            {/* Badges Unlocked */}
            <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-yellow-500/20 border border-yellow-500/30 flex items-center justify-center">
                  <Award className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <div className="text-lg font-bold text-white leading-tight">{summary.badges_unlocked}</div>
                  <div className="text-xs text-gray-400">Badges Unlocked</div>
                </div>
              </div>
              <Link to="/settings" className="text-[11px] text-blue-400 hover:text-blue-300 font-medium flex items-center gap-0.5 shrink-0">
                View All <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </div>

          <RecommendationsPage preview />

          <LearningPathPage preview />

          {/* ▸ 5. BOTTOM ROW: Recent Activity + Reading Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Recent Activity */}
            <div className="bg-[#111827]/60 backdrop-blur-md border border-gray-800/60 rounded-2xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-bold text-white">Recent Activity</h3>
              </div>
              <div className="space-y-2.5">
                {recentActivity.map((act, i) => {
                  const Icon = activityIcons[act.type] || BookOpen;
                  const colorCls = activityColors[act.color] || activityColors.blue;
                  return (
                    <div key={i} className="flex items-start gap-2.5">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center mt-0.5 shrink-0 ${colorCls}`}>
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-gray-200 truncate">{act.description}</p>
                        <span className="text-[10px] text-gray-500">{act.timestamp}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <StudentProgress />
          </div>

        </div>

        {/* ════════════ RIGHT SIDEBAR (4 cols) ════════════ */}
        <div className="xl:col-span-4 space-y-5">

          {/* ▸ 1. TODAY'S MISSIONS */}
          <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-400" />
                <h2 className="text-sm font-bold text-white">Today's Missions</h2>
              </div>
              <Link to="/quizzes" className="text-[11px] text-blue-400 hover:text-blue-300 font-medium">
                View All →
              </Link>
            </div>
            <div className="space-y-2">
              {missions.map((mission) => (
                <div
                  key={mission.id}
                  className="flex items-center justify-between p-2.5 rounded-xl bg-[#172033]/60 border border-gray-800/80 hover:border-gray-700 transition"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center transition ${
                        mission.completed ? 'bg-blue-600 text-white' : 'border border-gray-600 hover:border-gray-400'
                      }`}
                      role="checkbox" aria-checked={mission.completed} aria-disabled="true" aria-label={mission.title}
                    >
                      {mission.completed && <CheckCircle2 className="w-3.5 h-3.5" />}
                    </div>
                    <span className={`text-xs font-medium ${mission.completed ? 'text-gray-300' : 'text-gray-400'}`}>
                      {mission.title}
                    </span>
                  </div>
                  <span className="text-xs font-bold text-emerald-400">{mission.xp ? `+${mission.xp} XP` : 'Progress'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ▸ 2. AI ASSISTANT WIDGET */}
          <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-blue-400" />
                </div>
                <h3 className="text-sm font-bold text-white">AI Assistant</h3>
              </div>
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Online
              </span>
            </div>

            <p className="text-[11px] text-gray-400 mt-1 mb-2.5">
              Ask questions, get summaries, find books and more.
            </p>

            {/* Prompt capsules */}
            <div className="space-y-1 mb-2.5">
              {[
                'Where can I find Clean Code?',
                'Is there an online ebook for Python?',
                'Show me DBMS notes for Semester 5.',
                'Find Data Structures question banks.',
              ].map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handlePromptClick(prompt)}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg bg-[#172033]/80 hover:bg-blue-900/30 border border-gray-700/40 hover:border-blue-500/40 text-[11px] text-gray-300 hover:text-white transition flex items-center gap-1.5"
                >
                  <Sparkles className="w-3 h-3 text-blue-400 shrink-0" />
                  <span className="truncate">{prompt}</span>
                </button>
              ))}
            </div>

            {/* Conversation preview */}
            {aiResponses.length > 0 && (
              <div className="max-h-36 overflow-y-auto mb-2.5 space-y-1.5 pr-1">
                {aiResponses.map((res, i) => (
                  <div key={i} className="text-[11px] space-y-0.5">
                    <p className="text-blue-400 font-medium">Q: {res.query}</p>
                    <p className="text-gray-300 bg-gray-900/80 p-2 rounded-lg border border-gray-800 text-[10px] leading-relaxed">{res.answer}</p>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleAiSubmit} className="relative mt-1.5">
              <input
                type="text"
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                placeholder="Type your question..."
                className="w-full bg-[#172033] border border-gray-700/50 rounded-xl pl-3 pr-9 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={isAiLoading}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 w-6 h-6 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center justify-center text-white transition disabled:opacity-50"
              >
                {isAiLoading ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send className="w-3 h-3" />
                )}
              </button>
            </form>
          </div>

          <StudyRoomsSummary />
          <BadgeCollection earnedOnly />

          {/* ▸ 4. MORE BOOKS PROMO CARD */}
          <div className="bg-gradient-to-br from-[#122240] to-[#1a1c2e] border border-blue-900/40 rounded-2xl p-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <h4 className="text-sm font-bold text-white">More books,<br />more perspectives.</h4>
              <p className="text-[11px] text-blue-200/60 mt-1.5 leading-relaxed">
                Keep going, your next favorite book is just a search away.
              </p>
              <Link
                to="/books"
                className="mt-3 inline-flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold py-1.5 px-3 rounded-lg transition"
              >
                Browse Books <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
