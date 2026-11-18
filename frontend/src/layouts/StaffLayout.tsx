import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { BookOpen, Menu, X, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const groups = [
  { title: 'Overview', links: [['/admin/dashboard','Dashboard']] },
  { title: 'Library', links: [['/admin/books','Books'],['/admin/resources','Digital Library Management']] },
  { title: 'Operations', links: [['/admin/circulation','Circulation'],['/admin/study-moderation','Study Moderation']] },
  { title: 'Content', links: [['/admin/contributions','Contribution Moderation']] },
  { title: 'Academic', links: [['/admin/quizzes','Quiz Management']] },
  { title: 'People', links: [['/admin/student-data','Student Data'],['/admin/announcements','Announcements']] },
  { title: 'Insights', links: [['/admin/analytics','Analytics']] },
  { title: 'Tools', links: [['/admin/qr','QR Management']] },
  { title: 'Account', links: [['/admin/profile','Staff profile']] },
];

export default function StaffLayout() {
  const { user, logout } = useAuth(); const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  return <div className="min-h-screen bg-canvas text-ink">
    {open && <button aria-label="Close navigation overlay" onClick={()=>setOpen(false)} className="fixed inset-0 bg-black/60 z-30 lg:hidden"/>}
    <aside className={`fixed inset-y-0 left-0 w-64 z-40 bg-sidebar border-r border-line p-5 flex flex-col transition-transform ${open?'translate-x-0':'-translate-x-full'} lg:translate-x-0`}>
      <div className="flex items-center justify-between"><Link to="/admin/dashboard" className="flex items-center gap-2 font-bold text-xl text-white"><BookOpen className="text-blue-400"/>Book Bridge</Link><button aria-label="Close navigation" className="lg:hidden" onClick={()=>setOpen(false)}><X/></button></div>
      <p className="text-xs text-blue-400 mt-2">Staff workspace</p>
      <nav aria-label="Staff navigation" className="mt-5 space-y-4 flex-1 overflow-y-auto">{groups.map(group=><div key={group.title}><p className="text-xs uppercase tracking-widest text-secondary mb-2">{group.title}</p>{group.links.map(([to,label])=><NavLink key={to} to={to} onClick={()=>setOpen(false)} className={({isActive})=>`block rounded-lg px-3 py-2 text-sm ${isActive?'bg-accent/15 text-focus ring-1 ring-inset ring-accent/30':'text-secondary hover:bg-elevated hover:text-white'}`}>{label}</NavLink>)}</div>)}</nav>
      <button onClick={()=>{logout();navigate('/librarian/login',{replace:true});}} className="flex items-center gap-2 rounded-lg p-3 text-sm text-secondary hover:text-white"><LogOut size={17}/>Sign out</button>
    </aside>
    <div className="lg:ml-64"><header className="bg-surface border-b border-line px-5 md:px-8 py-4 flex items-center gap-4"><button aria-label="Open navigation" onClick={()=>setOpen(true)} className="lg:hidden"><Menu/></button><span className="text-sm text-secondary">Library administration</span><div className="ml-auto text-right"><p className="text-sm text-white">{user?.name}</p><p className="text-xs text-secondary capitalize">{user?.role}</p></div></header><main className="p-4 md:p-6 max-w-[1800px] mx-auto"><Outlet/></main></div>
  </div>;
}
