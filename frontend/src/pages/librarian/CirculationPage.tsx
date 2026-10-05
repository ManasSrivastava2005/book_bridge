import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../../services/api';
import type { Book, BorrowRecord, Reservation, User, Library } from '../../types';
import { libraryError } from '../../utils/library';

type StaffReservation=Reservation & {user:User;created_at:string};
type Data={loans:BorrowRecord[];students:User[];books:Book[];reservations:StaffReservation[];overdue:Set<number>;libraries:Library[]};
const button='rounded-xl border border-gray-700 bg-[#172033] px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-40';
const field='w-full rounded-xl border border-gray-700 bg-[#172033] p-2 text-sm text-white';
export default function CirculationPage(){
 const [params,setParams]=useSearchParams();
 const view=['borrowed','overdue','returned','reservations'].includes(params.get('view') || '')?params.get('view')!:'borrowed';
 const [data,setData]=useState<Data|null>(null);
 const [loading,setLoading]=useState(true);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const [busy,setBusy]=useState(false);
 const [search,setSearch]=useState('');
 const [library,setLibrary]=useState('');
 const [reservationStatus,setReservationStatus]=useState('active');
 const [student,setStudent]=useState(params.get('student') || '');
 const [book,setBook]=useState('');
 const [studentSearch,setStudentSearch]=useState('');
 const [bookSearch,setBookSearch]=useState('');
 const [due,setDue]=useState(()=>new Date(Date.now()+14*86400000).toISOString().slice(0,10));
 const [issueConfirmation,setIssueConfirmation]=useState<string|null>(null);
 useEffect(()=>setIssueConfirmation(null),[student,book,due]);
 const [page,setPage]=useState(0);
 const [confirm,setConfirm]=useState<{kind:'return'|'cancel'|'release'|'renew'|'ready';id:number;label:string;requestId?:string;due?:string}|null>(null);
 const [renewalHistory,setRenewalHistory]=useState<{old_due_date:string;new_due_date:string;created_at:string}[]|null>(null);
 const [historyLoan,setHistoryLoan]=useState<number|null>(null);
 const showHistory=async(id:number)=>{setBusy(true);setError('');try{const res=await api.get(`/admin/loans/${id}/renewals`);setRenewalHistory(res.data);setHistoryLoan(id);}catch(e){setError(libraryError(e,'Could not load renewal history.'));}finally{setBusy(false);}};
 const request=useRef(0);
 const load=async()=>{
  const sequence=++request.current;setLoading(true);setError('');
  try{
   const [loans,students,books,reservations,overdue,libraries]=await Promise.all([api.get('/borrows/'),api.get('/admin/students'),api.get('/books/'),api.get('/admin/reservations'),api.get('/admin/overdue-books'),api.get('/libraries/')]);
   if(sequence===request.current)setData({loans:loans.data,students:students.data,books:books.data,reservations:reservations.data,overdue:new Set(overdue.data.map((x:{borrow_id:number})=>x.borrow_id)),libraries:libraries.data});
  }catch(e){if(sequence===request.current)setError(libraryError(e,'Could not load circulation. Displayed records may be out of date.'));}
  finally{if(sequence===request.current)setLoading(false);}
 };
 useEffect(()=>{void load();return()=>{request.current++;};},[]);
 useEffect(()=>setPage(0),[search,library,view,reservationStatus]);
 const act=async(action:()=>Promise<unknown>,message:string)=>{
  setBusy(true);setNotice('');setError('');
  try{await action();setNotice(message);setConfirm(null);await load();}
  catch(e){setError(libraryError(e,'The action could not be completed. Refresh the records before trying again.'));}
  finally{setBusy(false);}
 };
 const disabled=loading || busy || !!error;
 const term=search.trim().toLowerCase();
 const matches=(item:{book?:Book;user?:User})=>(!library || item.book?.library_id===Number(library)) && (!term || [item.book?.title,item.book?.isbn,item.user?.name,item.user?.email,item.user?.student_id].some(value=>value?.toLowerCase().includes(term)));
 const loans=(data?.loans || []).filter(l=>matches(l) && (view==='overdue'?data!.overdue.has(l.id):l.status===view));
 const reservations=(data?.reservations || []).filter(r=>matches(r) && (reservationStatus==='active'?['pending','ready'].includes(r.status):r.status===reservationStatus));
 const count=view==='reservations'?reservations.length:loans.length;
 const currentPage=Math.min(page,Math.max(0,Math.ceil(count/25)-1));
 const held=data?.reservations.some(r=>r.user_id===Number(student) && r.book_id===Number(book) && r.status==='ready');
 const selectedStudent=data?.students.find(u=>u.id===Number(student));
 const selectedBook=data?.books.find(b=>b.id===Number(book));
 const issueBook=()=>{if(!issueConfirmation || !selectedBook)return;void act(()=>api.post('/admin/loans',{student_id:Number(student),book_id:Number(book),library_id:selectedBook.library_id,due_date:`${due}T23:59:59`,request_id:issueConfirmation}).then(()=>{setIssueConfirmation(null);setBook('');}),'Book issued. Loan and reservation history updated.');};
 const cancelOrReturn=()=>{
  if(!confirm)return;
  const {kind,id}=confirm;
  if(kind==='ready'){void act(()=>api.post(`/admin/reservations/${id}/ready`),'Copy marked ready for pickup. Student notified.');return;}
  if(kind==='renew'){void act(()=>api.post(`/admin/loans/${id}/renew`,{request_id:confirm.requestId,expected_due_date:confirm.due}),'Loan renewed. Renewal recorded in history.');return;}
  void act(()=>kind==='return'?api.post(`/borrows/${id}/return`):kind==='cancel'?api.delete(`/reservations/${id}`):api.post(`/admin/reservations/${id}/release`),kind==='return'?'Return recorded. Any waiting reservation received the copy.':kind==='cancel'?'Reservation cancelled.':'Held copy released to the next waiting student or available inventory.');
 };
 return <div className="max-w-[1600px] mx-auto space-y-5 pb-10">
  <header className="rounded-2xl border border-gray-800 bg-[#111827] p-5"><Link to="/admin/dashboard" className="text-cyan-400 text-sm">← Librarian Hub</Link><h1 className="text-2xl text-white font-bold mt-2">Circulation</h1><p className="text-sm text-gray-400 mt-1">Issue books, record returns, and manage waiting and held reservations.</p></header>
  <form className="rounded-2xl border border-gray-800 bg-[#111827] p-5 space-y-3" onSubmit={e=>{e.preventDefault();setIssueConfirmation(crypto.randomUUID());}}>
   <h2 className="text-white font-semibold">Issue a book</h2>
   <div className="grid md:grid-cols-2 gap-3">
    <label className="text-sm text-gray-300">Find student<input className={field} value={studentSearch} onChange={e=>setStudentSearch(e.target.value)} placeholder="Name, student ID or email"/></label>
    <label className="text-sm text-gray-300">Find book<input className={field} value={bookSearch} onChange={e=>setBookSearch(e.target.value)} placeholder="Title, author or ISBN"/></label>
    <label className="text-sm text-gray-300">Student<select aria-label="Student" required value={student} onChange={e=>setStudent(e.target.value)} className={field} disabled={disabled}><option value="">Select a student</option>{data?.students.filter(u=>String(u.id)===student || [u.name,u.student_id,u.email].some(v=>v?.toLowerCase().includes(studentSearch.trim().toLowerCase()))).map(u=><option value={u.id} key={u.id}>{u.name} · {u.student_id || u.email}</option>)}</select></label>
    <label className="text-sm text-gray-300">Book<select aria-label="Book" required value={book} onChange={e=>setBook(e.target.value)} className={field} disabled={disabled}><option value="">Select a book</option>{data?.books.filter(b=>String(b.id)===book || [b.title,b.author,b.isbn].some(v=>v?.toLowerCase().includes(bookSearch.trim().toLowerCase()))).map(b=><option key={b.id} value={b.id}>{b.title} · {b.available_copies} available</option>)}</select></label>
    <label className="text-sm text-gray-300">Due date<input type="date" required className={field} value={due} onChange={e=>setDue(e.target.value)} disabled={disabled}/></label>
    <div className="text-sm text-gray-300">Issuing library<p className="mt-2">{selectedBook?data?.libraries.find(l=>l.id===selectedBook.library_id)?.name || 'Legacy book — no library assigned':'Select a book to see its library'}</p></div>
   </div>
   {selectedStudent && <p className="text-sm text-gray-400">{selectedStudent.name} · {selectedStudent.student_id || 'No student ID'} · {selectedStudent.email} · Membership: {data?.libraries.find(l=>l.id===selectedStudent.library_id)?.name || 'Unassigned'} · {data?.loans.filter(l=>l.user_id===selectedStudent.id && l.status==='borrowed').length} active loans</p>}
   {held && <p className="text-xs text-emerald-400">A reserved copy is ready for this student and will be used for checkout.</p>}
   <button className={button} disabled={disabled || !student || !book}>Review checkout</button>
   {issueConfirmation && <section aria-label="Confirm checkout" className="border border-amber-700 rounded-xl p-3 space-y-3"><p className="text-white">Issue {selectedBook?.title} to {selectedStudent?.name}, due {due}?</p><button type="button" className={button} disabled={loading || busy} onClick={issueBook}>Confirm issue</button><button type="button" className={button} disabled={busy} onClick={()=>setIssueConfirmation(null)}>Cancel checkout</button></section>}
  </form>
  {renewalHistory && <section className="rounded-xl border border-gray-700 p-4"><div className="flex justify-between"><h2 className="text-white font-semibold">Renewal history · Loan #{historyLoan}</h2><button onClick={()=>setRenewalHistory(null)}>Close history</button></div>{renewalHistory.length?renewalHistory.map((r,i)=><p key={i} className="text-sm text-gray-400 mt-2">{new Date(r.created_at).toLocaleString()} · {new Date(r.old_due_date).toLocaleDateString()} → {new Date(r.new_due_date).toLocaleDateString()}</p>):<p className="text-gray-400 mt-2">No renewals recorded.</p>}</section>}
  <div className="flex flex-wrap gap-2">{[['borrowed','Active loans'],['overdue','Overdue'],['returned','Returned'],['reservations','Reservations']].map(([key,label])=><button key={key} aria-pressed={view===key} className={`${button} ${view===key?'!border-cyan-500 !text-cyan-300':''}`} onClick={()=>{setConfirm(null);setParams({view:key});}}>{label}</button>)}</div>
  <div className="grid md:grid-cols-[1fr_220px_180px_auto] gap-3"><input aria-label="Search circulation" placeholder="Book, ISBN, student or email" className={field} value={search} onChange={e=>setSearch(e.target.value)}/><select aria-label="Library filter" className={field} value={library} onChange={e=>setLibrary(e.target.value)}><option value="">All libraries</option>{data?.libraries.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select>{view==='reservations'?<select aria-label="Reservation status" className={field} value={reservationStatus} onChange={e=>setReservationStatus(e.target.value)}><option value="active">Waiting and held</option><option value="pending">Waiting</option><option value="ready">Ready for pickup</option><option value="fulfilled">Fulfilled</option><option value="cancelled">Cancelled</option></select>:<span/>}<button className={button} disabled={loading || busy} onClick={()=>void load()}>Refresh</button></div>
  {loading && <p role="status" className="text-gray-400">Loading circulation…</p>}{notice && <p role="status" className="text-emerald-300 text-sm">{notice}</p>}{error && <p role="alert" className="text-red-300 text-sm">{error}</p>}
  {confirm && <section aria-label="Confirm circulation action" className="rounded-2xl border border-amber-700 bg-[#172033] p-4 space-y-3"><p className="text-white text-sm">{confirm.kind==='return'?'Record physical return of':confirm.kind==='cancel'?'Cancel waiting reservation for':confirm.kind==='renew'?'Renew loan for':confirm.kind==='ready'?'Prepare a copy for':'Release the held copy of'} {confirm.label}?</p><div className="flex gap-2"><button className={button} disabled={disabled} onClick={cancelOrReturn}>Confirm {confirm.kind==='return'?'return':confirm.kind==='cancel'?'cancellation':confirm.kind==='renew'?'renewal':confirm.kind==='ready'?'ready for pickup':'release'}</button><button className={button} disabled={busy} onClick={()=>setConfirm(null)}>Keep unchanged</button></div></section>}
  {!loading && data && <>
   <p className="text-xs text-gray-400">{count} matching records</p>
   {view==='reservations'?<div className="space-y-3">{reservations.slice(currentPage*25,currentPage*25+25).map(r=>{
    const position=r.status==='pending'?data.reservations.filter(x=>x.book_id===r.book_id && x.status==='pending').findIndex(x=>x.id===r.id)+1:null;
    return <article key={r.id} className="rounded-2xl border border-gray-800 bg-[#111827] p-4 flex flex-wrap justify-between gap-3"><div className="min-w-0"><h2 className="text-white font-medium break-words">{r.book?.title || `Book #${r.book_id}`}</h2><p className="text-sm text-gray-400 break-words">{r.user.name} · {r.user.email}</p><p className="text-xs text-cyan-400 mt-1">{r.status==='pending'?`Waiting · Queue position ${position}`:r.status==='ready'?'Ready for pickup':r.status==='fulfilled'?'Fulfilled — issued to student':'Cancelled'}</p></div><div className="flex flex-wrap gap-2 items-center">{r.status==='pending' && <button className={button} disabled={disabled || !r.book?.available_copies || position!==1} onClick={()=>setConfirm({kind:'ready',id:r.id,label:`${r.book?.title} for ${r.user.name}`})}>Mark ready for pickup</button>}{r.status==='pending' && <button className={button} disabled={disabled} onClick={()=>setConfirm({kind:'cancel',id:r.id,label:`${r.book?.title} for ${r.user.name}`})}>Cancel reservation</button>}{r.status==='ready' && <><button className={button} disabled={disabled} onClick={()=>{setStudent(String(r.user_id));setBook(String(r.book_id));setNotice('Reserved student and book selected. Review the Issue a book form to check out.');window.scrollTo({top:0,behavior:'smooth'});}}>Prepare checkout</button><button className={button} disabled={disabled} onClick={()=>setConfirm({kind:'release',id:r.id,label:`${r.book?.title} for ${r.user.name}`})}>Release held copy</button></>}</div></article>;
   })}</div>:<div className="space-y-3">{loans.slice(currentPage*25,currentPage*25+25).map(l=><article key={l.id} className="rounded-2xl border border-gray-800 bg-[#111827] p-4 flex flex-wrap justify-between gap-3"><div className="min-w-0"><h2 className="text-white font-medium break-words">{l.book?.title || `Book #${l.book_id}`}</h2><p className="text-sm text-gray-400 break-words">{l.user?.name} · {l.user?.email}</p><p className={`text-xs mt-1 ${data.overdue.has(l.id)?'text-red-300':'text-gray-400'}`}>{data.overdue.has(l.id)?'Overdue · ':''}Due {new Date(l.due_date).toLocaleString()}{l.returned_at?` · Returned ${new Date(l.returned_at).toLocaleString()}`:''}</p></div><button className={button} disabled={disabled} onClick={()=>void showHistory(l.id)}>Renewal history</button>{l.status==='borrowed' && !data.overdue.has(l.id) && <button className={button} disabled={disabled} onClick={()=>setConfirm({kind:'renew',id:l.id,label:`${l.book?.title} for ${l.user?.name}`,requestId:crypto.randomUUID(),due:l.due_date})}>Renew</button>}{l.status==='borrowed' && <button className={`${button} self-center`} disabled={disabled} onClick={()=>setConfirm({kind:'return',id:l.id,label:`${l.book?.title} from ${l.user?.name}`})}>Record return</button>}</article>)}</div>}
   {!count && <p className="text-gray-500 py-8 text-center">No records match these filters.</p>}
   {count>25 && <div className="flex gap-3 items-center text-sm text-gray-400"><button className={button} disabled={currentPage===0} onClick={()=>setPage(currentPage-1)}>Previous</button>Page {currentPage+1} of {Math.ceil(count/25)}<button className={button} disabled={(currentPage+1)*25>=count} onClick={()=>setPage(currentPage+1)}>Next</button></div>}
  </>}
 </div>;
}
