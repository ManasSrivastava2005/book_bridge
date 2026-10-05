import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import CirculationAnalytics from '../../components/CirculationAnalytics';
import { libraryError } from '../../utils/library';

interface Dashboard {
 metrics: { pending_contributions:number;total_books:number;total_copies:number;available_books:number;issued_books:number;overdue_books:number;total_students:number;reservations:number };
 recent_books: {id:number;title:string;author:string;created_at:string}[];
 popular_books: {id:number;title:string;borrow_count:number;pending_reservations:number}[];
 demand_prediction: {book_id:number;title:string;current_available:number;total_copies:number;pending_reservations:number;risk_level:string}[];
 recent_activities: {id:number;user_name:string;book_title:string;date:string;status:string;is_overdue:boolean}[];
}
const link='rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-sm font-medium text-white';
export default function LibrarianDashboardPage() {
 const [data,setData]=useState<Dashboard|null>(null);
 const [error,setError]=useState('');
 const [loading,setLoading]=useState(true);
 const [attempt,setAttempt]=useState(0);
 useEffect(()=>{let active=true;setLoading(true);setError('');api.get('/admin/dashboard').then(r=>{if(active)setData(r.data);}).catch(e=>{if(active)setError(libraryError(e,'Could not load librarian dashboard.'));}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[attempt]);
 return <div className="max-w-[1600px] mx-auto space-y-6 pb-12">
  <header className="bg-[#111827] border border-gray-800 rounded-2xl p-6 flex flex-wrap justify-between items-center gap-4"><div><p className="text-xs text-amber-400 mb-1">Staff portal</p><h1 className="text-2xl font-bold text-white">Librarian Management Hub</h1><p className="text-sm text-gray-400 mt-2">Live inventory, circulation and reservation activity across Book Bridge.</p></div><div className="flex flex-wrap gap-2"><Link className={link} to="/admin/circulation">Manage circulation</Link><Link className={link} to="/admin/books">Manage catalog</Link><Link className={link} to="/admin/resources">Digital resources</Link></div></header>
  {loading && <p role="status" className="text-gray-400">Loading library activity…</p>}
  {error && <div role="alert" className="text-red-300">{error} <button className={link} onClick={()=>setAttempt(v=>v+1)}>Retry</button></div>}
  {!loading && !error && data && <>
   <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[
    ['Total books',data.metrics.total_books,'Distinct catalogue titles'],
    ['Total copies',data.metrics.total_copies,'Physical inventory'],
    ['Available copies',data.metrics.available_books,'Ready to issue'],
    ['Issued books',data.metrics.issued_books,'Active loans'],
    ['Overdue books',data.metrics.overdue_books,'Review in circulation'],
    ['Active reservations',data.metrics.reservations,'Waiting and held for pickup'],
    ['Pending contributions',data.metrics.pending_contributions,'Awaiting staff review'],
    ['Total students',data.metrics.total_students,'Registered student accounts'],
   ].map(([label,value,detail])=><article key={label} className="bg-[#111827] border border-gray-800 rounded-2xl p-4"><h2 className="text-xs text-gray-400">{label}</h2><p className="text-2xl font-bold text-white mt-2">{value}</p><p className="text-xs text-gray-500 mt-1">{detail}</p></article>)}</div>
   <div className="flex flex-wrap gap-3"><Link className="text-cyan-400 text-sm" to="/admin/circulation?view=overdue">Review overdue loans →</Link><Link className="text-cyan-400 text-sm" to="/admin/circulation?view=reservations">Manage reservation queue →</Link></div>
   <section className="bg-[#111827] border border-gray-800 rounded-2xl p-5"><h2 className="text-white font-semibold">Recently added books</h2><ul className="divide-y divide-gray-800 mt-3">{data.recent_books?.map(b=><li key={b.id} className="py-3"><Link className="text-cyan-300 text-sm" to={`/admin/books?search=${encodeURIComponent(b.title)}`}>{b.title}</Link><p className="text-xs text-gray-400">{b.author} · {new Date(b.created_at).toLocaleDateString()}</p></li>)}</ul>{!data.recent_books?.length && <p className="text-gray-500 mt-3">No books have been added yet.</p>}</section>
   <CirculationAnalytics />
   <div className="grid lg:grid-cols-2 gap-5">
    <section className="bg-[#111827] border border-gray-800 rounded-2xl p-5"><h2 className="text-white font-semibold">Popular books</h2><p className="text-xs text-gray-400 mt-1">Ranked from actual loans, reservations and reviews.</p><ul className="divide-y divide-gray-800 mt-3">{data.popular_books.map(b=><li key={b.id} className="py-3"><Link to={`/admin/books?search=${encodeURIComponent(b.title)}`} className="text-sm text-cyan-300">{b.title}</Link><p className="text-xs text-gray-400">{b.borrow_count} recorded loans · {b.pending_reservations} waiting</p></li>)}</ul>{!data.popular_books.length && <p className="text-gray-500 mt-3">No catalog activity yet.</p>}</section>
    <section className="bg-[#111827] border border-gray-800 rounded-2xl p-5"><h2 className="text-white font-semibold">Inventory pressure</h2><p className="text-xs text-gray-400 mt-1">Rule-based signals from availability and waiting lists. These are not trained ML forecasts.</p><ul className="divide-y divide-gray-800 mt-3">{data.demand_prediction.map(b=><li key={b.book_id} className="py-3"><p className="text-sm text-white">{b.title}</p><p className="text-xs text-gray-400">{b.current_available} of {b.total_copies} available · {b.pending_reservations} waiting</p><span className="text-xs text-amber-300">{b.risk_level}</span></li>)}</ul>{!data.demand_prediction.length && <p className="text-gray-500 mt-3">No inventory to assess.</p>}</section>
   </div>
   <section className="bg-[#111827] border border-gray-800 rounded-2xl p-5"><h2 className="text-white font-semibold">Recent loan records</h2><ul className="divide-y divide-gray-800 mt-3">{data.recent_activities.map(a=><li key={a.id} className="py-3 flex flex-wrap justify-between gap-2"><div><p className="text-sm text-white">{a.book_title}</p><p className="text-xs text-gray-400">{a.user_name} · {a.status}{a.is_overdue?' · Overdue':''}</p></div><time className="text-xs text-gray-500">{a.date?new Date(a.date).toLocaleString():'Date unavailable'}</time></li>)}</ul>{!data.recent_activities.length && <p className="text-gray-500 mt-3">No loan records yet.</p>}</section>
  </>}
 </div>;
}
