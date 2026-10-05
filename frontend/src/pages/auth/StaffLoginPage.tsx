import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { BookOpen, ShieldCheck, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function StaffLoginPage() {
  const { login, user, isLoading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(location.state?.restricted ? 'This portal is restricted to library staff.' : '');
  if (!isLoading && user && ['librarian', 'admin'].includes(user.role)) return <Navigate to="/admin/dashboard" replace />;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await login(email.trim(), password, true); navigate('/admin/dashboard', { replace: true }); }
    catch (e: any) { setError(e.response?.data?.detail || e.message || 'Unable to sign in. Please try again.'); }
    finally { setBusy(false); }
  };
  const field = 'w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500';
  return <main className="min-h-screen bg-[#0a0e1a] text-slate-200 flex items-center justify-center p-5">
    <div className="w-full max-w-5xl grid lg:grid-cols-2 rounded-3xl border border-slate-800 bg-[#111827] overflow-hidden shadow-2xl">
      <section className="p-8 lg:p-12 bg-gradient-to-br from-blue-950 to-[#111827]">
        <Link to="/login" className="inline-flex items-center gap-3 text-white font-bold text-2xl"><BookOpen className="h-9 w-9 text-blue-400" />Book Bridge</Link>
        <div className="mt-10"><ShieldCheck className="h-10 w-10 text-blue-400 mb-5" /><p className="text-blue-300 text-sm uppercase tracking-widest">Library operations</p><h1 className="text-3xl font-semibold text-white mt-3">Your library, connected.</h1><p className="text-slate-400 leading-relaxed mt-4">Manage collections, circulation, and academic resources from your staff workspace.</p></div>
        <p className="text-sm text-slate-500 mt-8">For authorized librarians and administrators.</p>
      </section>
      <section className="p-8 lg:p-12">
        <h2 className="text-2xl font-semibold text-white">Staff sign in</h2><p className="text-slate-400 mt-2 mb-7">Use your existing Book Bridge staff account.</p>
        {error && <div role="alert" className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}
        <form onSubmit={submit} className="space-y-5">
          <label className="block text-sm">Email<input className={`${field} mt-2`} type="email" autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)} required disabled={busy} /></label>
          <div><label htmlFor="staff-password" className="block text-sm mb-2">Password</label><div className="relative"><input id="staff-password" className={`${field} pr-12`} type={visible?'text':'password'} autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required disabled={busy}/><button type="button" aria-label={visible?'Hide password':'Show password'} onClick={()=>setVisible(!visible)} className="absolute right-4 top-3.5 text-slate-400">{visible?<EyeOff size={20}/>:<Eye size={20}/>}</button></div></div>
          <button disabled={busy || isLoading} className="w-full rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 py-3 font-semibold text-white">{busy?'Signing in…':'Sign in to staff portal'}</button>
        </form>
        <Link to="/login" className="block text-center text-sm text-blue-400 mt-7">Student sign in</Link>
      </section>
    </div>
  </main>;
}
