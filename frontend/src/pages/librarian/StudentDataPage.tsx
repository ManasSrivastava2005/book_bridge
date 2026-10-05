import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import type { User, Library, BorrowRecord, Reservation } from '../../types';
import { libraryError } from '../../utils/library';

type Directory={items:User[];total:number;branches:string[]};
type Detail={student:User;academic:{college:string|null;program:string|null;specialization:string|null;subjects:{id:number|null;title:string;source:string}[]};loans:BorrowRecord[];reservations:Reservation[];overdue_ids:number[]};
const field='w-full rounded-xl border border-gray-700 bg-[#172033] p-2 text-white text-sm';
const button='rounded-xl border border-gray-700 bg-[#172033] px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-40';
export default function StudentDataPage(){
 const [directory,setDirectory]=useState<Directory>({items:[],total:0,branches:[]});
 const [libraries,setLibraries]=useState<Library[]>([]);
 const [search,setSearch]=useState(''),[branch,setBranch]=useState(''),[semester,setSemester]=useState(''),[membership,setMembership]=useState('');
 const [page,setPage]=useState(1),[selected,setSelected]=useState<number|null>(null),[detail,setDetail]=useState<Detail|null>(null);
 const [library,setLibrary]=useState(''),[loading,setLoading]=useState(true),[detailLoading,setDetailLoading]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[refresh,setRefresh]=useState(0);
 useEffect(()=>{let live=true;api.get('/libraries/').then(r=>{if(live)setLibraries(r.data);}).catch(e=>{if(live)setError(libraryError(e,'Could not load libraries.'));});return()=>{live=false;};},[]);
 useEffect(()=>{let live=true;setLoading(true);setError('');const timer=setTimeout(()=>{api.get('/admin/student-data',{params:{search,branch,semester:semester||undefined,library_id:membership||undefined,page}}).then(r=>{if(live)setDirectory(r.data);}).catch(e=>{if(live)setError(libraryError(e,'Could not load Student Data.'));}).finally(()=>{if(live)setLoading(false);});},200);return()=>{live=false;clearTimeout(timer);};},[search,branch,semester,membership,page,refresh]);
 useEffect(()=>{let live=true;setDetail(null);if(selected===null){setDetailLoading(false);return;}setDetailLoading(true);api.get(`/admin/student-data/${selected}`).then(r=>{if(live){setDetail(r.data);setLibrary(r.data.student.library_id?String(r.data.student.library_id):'');}}).catch(e=>{if(live)setError(libraryError(e,'Could not load student details.'));}).finally(()=>{if(live)setDetailLoading(false);});return()=>{live=false;};},[selected,refresh]);
 const saveMembership=async()=>{if(selected===null)return;setBusy(true);setError('');setNotice('');try{await api.put(`/admin/users/${selected}/membership`,{library_id:library?Number(library):null});setNotice('Library membership updated.');setRefresh(v=>v+1);}catch(e){setError(libraryError(e,'Could not update membership.'));}finally{setBusy(false);}};
 return <div className="max-w-[1600px] mx-auto space-y-5 pb-10">
  <header><h1 className="text-2xl font-bold text-white">Student Data</h1><p className="text-gray-400 text-sm mt-1">Find students, review academic and circulation records, and manage library membership.</p></header>
  <div className="grid md:grid-cols-4 gap-3">
   <label className="text-sm text-gray-300">Search students<input className={field} placeholder="Name, student ID or email" value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}}/></label>
   <label className="text-sm text-gray-300">Branch<select aria-label="Branch" className={field} value={branch} onChange={e=>{setBranch(e.target.value);setPage(1);}}><option value="">All branches</option>{directory.branches.map(b=><option key={b}>{b}</option>)}</select></label>
   <label className="text-sm text-gray-300">Semester<select aria-label="Semester" className={field} value={semester} onChange={e=>{setSemester(e.target.value);setPage(1);}}><option value="">All semesters</option>{Array.from({length:20},(_,i)=>i+1).map(n=><option key={n}>{n}</option>)}</select></label>
   <label className="text-sm text-gray-300">Membership filter<select aria-label="Membership filter" className={field} value={membership} onChange={e=>{setMembership(e.target.value);setPage(1);}}><option value="">All memberships</option><option value="0">Unassigned</option>{libraries.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
  </div>
  {error && <p role="alert" className="text-red-300">{error}</p>}{notice && <p role="status" className="text-emerald-300">{notice}</p>}
  {detailLoading && <p role="status" className="text-gray-400">Loading student details…</p>}
  {detail && <section aria-label="Student details" className="rounded-2xl border border-cyan-900 bg-[#111827] p-5 space-y-4">
   <div className="flex justify-between gap-3"><h2 className="font-bold text-xl text-white">{detail.student.name}</h2><button className={button} onClick={()=>setSelected(null)}>Close details</button></div>
   <p className="text-sm text-gray-300">{detail.student.student_id || 'Student ID not recorded'} · {detail.student.email} · {detail.student.branch || 'Branch not recorded'} · Semester {detail.student.semester || '—'}</p>
   <p className="text-sm text-gray-400">College: {detail.academic.college || 'Not recorded'} · Program: {detail.academic.program || 'Not recorded'} · Specialization: {detail.academic.specialization || 'Not recorded'}</p>
   <div><h3 className="font-semibold text-white">Selected subjects</h3><p className="text-sm text-gray-400">{detail.academic.subjects.map(s=>s.title).join(', ') || 'No subjects selected.'}</p></div>
   <div className="flex flex-wrap items-end gap-3"><label className="text-sm text-gray-300 grow">Library membership<select aria-label="Library membership" className={field} value={library} disabled={busy} onChange={e=>setLibrary(e.target.value)}><option value="">No library membership</option>{libraries.filter(l=>l.is_active || l.id===detail.student.library_id).map(l=><option key={l.id} value={l.id} disabled={!l.is_active}>{l.name}{!l.is_active?' (inactive)':''}</option>)}</select></label><button className={button} disabled={busy} onClick={()=>void saveMembership()}>Save membership</button><Link className={button} to={`/admin/circulation?student=${detail.student.id}`}>Issue book to student</Link></div>
   <div><h3 className="font-semibold text-white">Borrowing history</h3>{detail.loans.length?detail.loans.map(l=><p key={l.id} className={`text-sm mt-2 ${detail.overdue_ids.includes(l.id)?'text-red-300':'text-gray-400'}`}>{l.book?.title} · {l.status} · Due {new Date(l.due_date).toLocaleString()}{detail.overdue_ids.includes(l.id)?' · Overdue':''}{l.returned_at?` · Returned ${new Date(l.returned_at).toLocaleString()}`:''}</p>):<p className="text-sm text-gray-400">No borrowing history.</p>}</div>
   <div><h3 className="font-semibold text-white">Reservations</h3>{detail.reservations.length?detail.reservations.map(r=><p key={r.id} className="text-sm text-gray-400 mt-2">{r.book?.title} · {r.status==='ready'?'Ready for pickup':r.status==='pending'?'Pending':r.status==='fulfilled'?'Fulfilled':'Cancelled'}</p>):<p className="text-sm text-gray-400">No reservations.</p>}</div>
  </section>}
  {loading?<p role="status" className="text-gray-400">Loading Student Data…</p>:<><p className="text-sm text-gray-400">{directory.total} matching students</p>{directory.items.map(u=><article key={u.id} className="rounded-2xl border border-gray-800 bg-[#111827] p-4 flex flex-wrap justify-between gap-3"><div><h2 className="text-white font-semibold">{u.name}</h2><p className="text-sm text-gray-400">{u.student_id || 'No student ID'} · {u.email}</p><p className="text-xs text-gray-400">{u.branch || 'No branch'} · Semester {u.semester || '—'} · {libraries.find(l=>l.id===u.library_id)?.name || 'Unassigned membership'}</p></div><button className={button} onClick={()=>{setSelected(u.id);setNotice('');}}>View student</button></article>)}{!directory.total && <p className="text-gray-400">No students match these filters.</p>}</>}
  <footer className="flex items-center gap-3 text-sm text-gray-400"><button className={button} disabled={loading || page<=1} onClick={()=>setPage(p=>p-1)}>Previous</button>Page {page} of {Math.max(1,Math.ceil(directory.total/20))}<button className={button} disabled={loading || page*20>=directory.total} onClick={()=>setPage(p=>p+1)}>Next</button><button className={button} disabled={loading} onClick={()=>setRefresh(v=>v+1)}>Refresh</button></footer>
 </div>;
}
