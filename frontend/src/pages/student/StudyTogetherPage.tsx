import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import StudyFiles from '../../components/StudyFiles';
import api from '../../services/api';
import { libraryError } from '../../utils/library';

interface Room { is_private:boolean; invite_code?:string|null; id:number; owner_id:number; title:string; subject:string; description:string; archived:boolean; member_count:number; is_member:boolean }
interface Message { id:number; user_id:number; author:string; body:string; created_at:string; can_delete:boolean;can_edit:boolean;edited_at:string|null;deleted_at:string|null;reply:{id:number;author:string;body:string}|null }
interface Page<T> { items:T[]; next_before:number|null }
const panel='rounded-2xl border border-gray-800 bg-[#111827] p-5';
const field='w-full rounded-xl border border-gray-700 bg-[#172033] p-2.5 text-sm text-white';
const button='rounded-xl bg-blue-600 hover:bg-blue-500 px-4 py-2 text-sm text-white disabled:opacity-40';
const secondary='rounded-xl border border-gray-700 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:opacity-40';

function RoomDirectory() {
  const navigate=useNavigate();
  const [rooms,setRooms]=useState<Room[]>([]);
  const [next,setNext]=useState<number|null>(null);
  const [mine,setMine]=useState(false);
  const [search,setSearch]=useState('');
  const [query,setQuery]=useState('');
  const [title,setTitle]=useState('');
  const [subject,setSubject]=useState('');
  const [description,setDescription]=useState('');
  const [isPrivate,setIsPrivate]=useState(false);
  const [loading,setLoading]=useState(true);
  const [creating,setCreating]=useState(false);
  const [error,setError]=useState('');
  const [createError,setCreateError]=useState('');
  const sequence=useRef(0);
  const load=async(before?:number)=>{
    const request=++sequence.current;setLoading(true);setError('');
    try { const res=await api.get<Page<Room>>('/study/rooms',{params:{mine,search:query,before}});
      if(request===sequence.current){setRooms(current=>before?[...current,...res.data.items]:res.data.items);setNext(res.data.next_before);}
    } catch(e){if(request===sequence.current)setError(libraryError(e,'Could not load study rooms.'));}
    finally{if(request===sequence.current)setLoading(false);}
  };
  useEffect(()=>{setRooms([]);setNext(null);void load();return()=>{sequence.current++;};},[mine,query]);
  const create=async()=>{
    if(creating)return;setCreating(true);setCreateError('');
    try{const res=await api.post<Room>('/study/rooms',{title,subject,description,is_private:isPrivate});navigate(`/study-together/${res.data.id}`);}
    catch(e){setCreateError(libraryError(e,'Could not create the room.'));}finally{setCreating(false);}
  };
  return <div className="max-w-6xl mx-auto space-y-5 pb-10">
    <header className={panel}><h1 className="text-2xl font-bold text-white">Study Together</h1><p className="text-sm text-gray-400 mt-2">Find a study group, share questions, and work through a subject together.</p><p className="text-xs text-gray-500 mt-2">Public rooms are discoverable by signed-in users; invitation-only rooms require a link from the owner. Join a room to read and post. Library staff can moderate discussions. Personal notes are never shared automatically.</p></header>
    <details className={panel}><summary className="text-white font-semibold cursor-pointer">Create a study room</summary>
      <form className="space-y-3 mt-4" onSubmit={e=>{e.preventDefault();void create();}}>
        <div className="grid sm:grid-cols-2 gap-3"><label className="text-sm text-gray-300">Room title<input className={field} required maxLength={120} value={title} onChange={e=>setTitle(e.target.value)}/></label><label className="text-sm text-gray-300">Subject (optional)<input className={field} maxLength={100} value={subject} onChange={e=>setSubject(e.target.value)}/></label></div>
        <label className="block text-sm text-gray-300">Study goal<textarea className={field} maxLength={2000} rows={3} value={description} onChange={e=>setDescription(e.target.value)} placeholder="What will this group work on?"/></label>
        <label className="block text-sm text-gray-300"><input type="checkbox" checked={isPrivate} onChange={e=>setIsPrivate(e.target.checked)}/> Invitation-only room</label>
        {createError && <p role="alert" className="text-sm text-red-300">{createError}</p>}
        <button className={button} disabled={creating || !title.trim()}>{creating?'Creating…':'Create room'}</button>
      </form>
    </details>
    <div className="flex flex-wrap gap-3 items-center"><button className={mine?secondary:button} aria-pressed={!mine} onClick={()=>setMine(false)}>Discover rooms</button><button className={mine?button:secondary} aria-pressed={mine} onClick={()=>setMine(true)}>My rooms</button>
      <form className="flex gap-2 flex-1 min-w-0" onSubmit={e=>{e.preventDefault();setQuery(search.trim());}}><input aria-label="Search study rooms" className={`${field} min-w-0`} maxLength={120} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Title or subject"/><button className={secondary}>Search</button></form>
      <button className={secondary} disabled={loading} onClick={()=>void load()}>Refresh rooms</button>
    </div>
    {error && <p role="alert" className="text-red-300 text-sm">{error} <button className="underline" onClick={()=>void load()}>Retry</button></p>}
    <div className="grid md:grid-cols-2 gap-4">{rooms.map(room=><article key={room.id} className={panel}><div className="flex gap-2 justify-between text-xs"><span className="text-blue-400 break-words min-w-0">{room.subject}</span><span className="text-gray-400 shrink-0">{room.archived?'Archived':`${room.member_count} members`}</span></div><h2 className="font-semibold text-white mt-2 break-words">{room.title}</h2><p className="text-sm text-gray-400 mt-2 line-clamp-3 break-words">{room.description || 'Join to discuss this subject.'}</p><Link className={`${secondary} inline-block mt-4`} to={`/study-together/${room.id}`}>{room.is_member?'Open discussion':'View room'}</Link></article>)}</div>
    {loading && <p role="status" className="text-sm text-gray-400">Loading study rooms…</p>}
    {!loading && !error && !rooms.length && <p className="text-gray-400 text-sm py-6">{mine?'You have not joined any matching rooms yet.':'No matching rooms yet. Create one to start a study group.'}</p>}
    {next && <button className={secondary} disabled={loading} onClick={()=>void load(next)}>Load more rooms</button>}
  </div>;
}

function StudyRoomView({id}:{id:string}) {
  const {user}=useAuth();
  const [params]=useSearchParams();
  const invite=params.get('invite') || undefined;
  const [live,setLive]=useState(true);
  const [report,setReport]=useState<number|null>(null);
  const [reason,setReason]=useState('');
  const [room,setRoom]=useState<Room|null>(null);
  const [messages,setMessages]=useState<Message[]>([]);
  const [older,setOlder]=useState<number|null>(null);
  const [body,setBody]=useState('');
  const [reply,setReply]=useState<Message|null>(null),[editing,setEditing]=useState<Message|null>(null),[editBody,setEditBody]=useState(''),[roomEdit,setRoomEdit]=useState<{title:string;subject:string;description:string}|null>(null);
  const [participants,setParticipants]=useState<{user_id:number;name:string;role:string;recently_active:boolean}[]>([]);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [confirmation,setConfirmation]=useState<'leave'|'archive'|number|null>(null);
  const retry=useRef<{body:string;client_id:string;reply_to_id:number|null}|null>(null);
  const sequence=useRef(0);
  const staff=user?.role==='admin'||user?.role==='librarian';
  const load=async(silent=false)=>{
    const request=++sequence.current;if(!silent)setLoading(true);setError('');
    try{
      const res=await api.get<Room>(`/study/rooms/${id}`,{params:{invite}});
      const discussion=res.data.is_member||staff?await api.get<Page<Message>>(`/study/rooms/${id}/messages`):null;
      if(res.data.is_member && !document.hidden)await api.post(`/study/rooms/${id}/presence`);
      const people=res.data.is_member||staff?await api.get(`/study/rooms/${id}/participants`):null;
      if(request===sequence.current){setParticipants(people?.data.items || []);setRoom(res.data);setMessages(discussion?.data.items || []);setOlder(discussion?.data.next_before || null);}
    }catch(e){if(request===sequence.current)setError(libraryError(e,'Could not load this study room.'));}
    finally{if(request===sequence.current)setLoading(false);}
  };
  useEffect(()=>{void load();return()=>{sequence.current++;};},[id,staff,invite]);
  useEffect(()=>{if(!live || busy || loading || !room?.is_member)return;let running=false;const timer=window.setInterval(()=>{if(!document.hidden && !running){running=true;void load(true).finally(()=>{running=false;});}},10000);return()=>window.clearInterval(timer);},[id,staff,invite,live,busy,loading,room?.is_member]);
  const action=async(task:()=>Promise<unknown>,message:string)=>{
    if(busy)return;setBusy(true);setError('');setNotice('');
    try{await task();setConfirmation(null);setNotice(message);await load();}
    catch(e){setError(libraryError(e,'The action could not be completed. Please try again.'));}
    finally{setBusy(false);}
  };
  const post=async()=>{
    const text=body.trim();if(!text || busy)return;
    if(!retry.current || retry.current.body!==text || retry.current.reply_to_id!==(reply?.id||null))retry.current={body:text,client_id:crypto.randomUUID(),reply_to_id:reply?.id||null};
    await action(async()=>{await api.post(`/study/rooms/${id}/messages`,retry.current);retry.current=null;setBody('');setReply(null);},'Your message was posted.');
  };
  const loadOlder=async()=>{
    if(!older || busy)return;setLive(false);setBusy(true);setError('');
    try{const res=await api.get<Page<Message>>(`/study/rooms/${id}/messages`,{params:{before:older}});setMessages(current=>[...res.data.items,...current]);setOlder(res.data.next_before);}
    catch(e){setError(libraryError(e,'Could not load older messages.'));}finally{setBusy(false);}
  };
  const moderate=!!room && (room.owner_id===user?.id || staff);
  return <div className="max-w-5xl mx-auto space-y-5 pb-10">
    <Link to="/study-together" className="text-sm text-cyan-400">← All study rooms</Link>
    {error && <div role="alert" className="text-red-300 text-sm">{error} <button className="underline" disabled={busy || loading} onClick={()=>void load()}>Refresh room</button></div>}
    {notice && <p role="status" className="text-emerald-300 text-sm">{notice}</p>}
    {loading && <p role="status" className="text-sm text-gray-400">Loading room…</p>}
    {room && <>
      <header className={panel}><p className="text-xs text-blue-400 break-words">{room.subject} · {room.member_count} members</p><h1 className="text-2xl text-white font-bold mt-2 break-words">{room.title}</h1><p className="text-sm text-gray-400 mt-2 whitespace-pre-wrap break-words">{room.description}</p>
        {room.archived && <p className="text-amber-300 text-sm mt-3">Archived — discussion is read-only.</p>}
        <div className="flex flex-wrap gap-2 mt-4">
          {!room.is_member && !room.archived && <button className={button} disabled={busy || loading} onClick={()=>void action(()=>api.post(`/study/rooms/${id}/join`,null,{params:{invite}}),'You joined the room.')}>Join room</button>}
          {room.is_member && room.owner_id!==user?.id && <button className={secondary} disabled={busy || loading} onClick={()=>setConfirmation('leave')}>Leave room</button>}
          {moderate && <button className={secondary} disabled={busy} onClick={()=>setRoomEdit({title:room.title,subject:room.subject,description:room.description})}>Edit room details</button>}
          {moderate && <button className={secondary} disabled={busy || loading} onClick={()=>setConfirmation('archive')}>{room.archived?'Reopen room':'Archive room'}</button>}
          <button className={secondary} disabled={busy || loading} onClick={()=>void load()}>Refresh discussion</button>
        </div>
        <p className="text-xs text-gray-500 mt-3">Discussions refresh every 10 seconds while this tab is visible. Members and library staff can read posts.</p>
        <label className="block text-xs text-gray-400 mt-2"><input type="checkbox" checked={live} onChange={e=>setLive(e.target.checked)}/> Automatic discussion updates</label>
        {room.owner_id===user?.id && <label className="block text-xs text-gray-400 mt-3">Invitation link (share with your study group)<input aria-label="Invitation link" className={field} readOnly value={`${window.location.origin}/study-together/${id}${room.invite_code?'?invite='+encodeURIComponent(room.invite_code):''}`} onFocus={e=>e.target.select()}/></label>}
      </header>
      {roomEdit && <form className={panel} onSubmit={e=>{e.preventDefault();void action(async()=>{await api.patch(`/study/rooms/${id}/details`,roomEdit);setRoomEdit(null);},'Room details updated.');}}><label className="text-sm text-gray-300">Room title<input className={field} required maxLength={120} value={roomEdit.title} onChange={e=>setRoomEdit({...roomEdit,title:e.target.value})}/></label><label className="text-sm text-gray-300">Room subject (optional)<input className={field} maxLength={100} value={roomEdit.subject} onChange={e=>setRoomEdit({...roomEdit,subject:e.target.value})}/></label><label className="text-sm text-gray-300">Room description<textarea aria-label="Room description" className={field} maxLength={2000} value={roomEdit.description} onChange={e=>setRoomEdit({...roomEdit,description:e.target.value})}/></label><button className={button} disabled={busy}>Save room details</button><button type="button" className={secondary} onClick={()=>setRoomEdit(null)}>Cancel editing room</button></form>}
      {(room.is_member || staff) && <section className={panel}><h2 className="text-white font-semibold">Participants ({participants.length})</h2><p className="text-xs text-gray-400 mt-1">Active means seen in this room within 3 minutes; it is not guaranteed live presence.</p><ul className="flex flex-wrap gap-3 mt-3">{participants.map(p=><li key={p.user_id} className="text-sm text-gray-300"><span className={p.recently_active?'text-emerald-400':'text-gray-500'}>{p.recently_active?'●':'○'}</span> {p.name} · {p.role==='OWNER'?'Room admin':p.recently_active?'Recently active':'Member'}</li>)}</ul></section>}
      {(room.is_member || staff) && <StudyFiles roomId={id} canUpload={room.is_member && !room.archived}/>}
      {report!==null && <form className={panel} onSubmit={e=>{e.preventDefault();void action(async()=>{await api.post(`/study/rooms/${id}/messages/${report}/report`,{reason});setReport(null);setReason('');},'Report sent to library staff.');}}><label className="text-sm text-gray-300">Reason for report<textarea className={field} maxLength={1000} required value={reason} onChange={e=>setReason(e.target.value)}/></label><div className="flex gap-2 mt-2"><button className={button} disabled={busy || !reason.trim()}>Submit report</button><button type="button" className={secondary} onClick={()=>setReport(null)}>Cancel report</button></div></form>}
      {typeof confirmation==='string' && <div role="alert" className={`${panel} space-y-3`}><p className="text-sm text-gray-200">{confirmation==='leave'?'Leave this room? Your existing messages will remain.':confirmation==='archive'?(room.archived?'Reopen this room for joining and discussion?':'Archive this room? Existing discussion stays available to members.'): 'Delete this message? A deleted-message placeholder and reply references will remain.'}</p><div className="flex gap-2"><button className={button} disabled={busy || loading} onClick={()=>{
        if(confirmation==='leave')void action(()=>api.post(`/study/rooms/${id}/leave`),'You left the room.');
        else if(confirmation==='archive')void action(()=>api.patch(`/study/rooms/${id}`,{archived:!room.archived}),room.archived?'Room reopened.':'Room archived.');

      }}>Confirm</button><button className={secondary} disabled={busy} onClick={()=>setConfirmation(null)}>Cancel</button></div></div>}
      {!room.is_member && !staff ? <p className="text-gray-400 text-sm">{room.archived?'This room is archived and no longer accepts new members.':'Join this room to read and contribute to its discussion.'}</p> : <section aria-label="Room discussion" className={`${panel} space-y-4`}>
        <h2 className="text-white font-semibold">Discussion</h2>
        {older && <button className={secondary} disabled={busy || loading} onClick={()=>void loadOlder()}>Load older messages</button>}
        {!messages.length && <p className="text-sm text-gray-500">No messages yet. Start with a question or a study goal.</p>}
        {messages.map(message=><article key={message.id} data-message-id={message.id} className="rounded-xl bg-[#172033] p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-medium text-blue-300 break-words">{message.author}{message.user_id===user?.id?' (you)':''}</p><time className="text-xs text-gray-500">{new Date(message.created_at).toLocaleString()}{message.edited_at?' · edited':''}</time></div>{message.reply&&<blockquote className="border-l-2 border-blue-400 pl-3 my-2 text-xs text-blue-200">↳ {message.reply.author}: {message.reply.body}</blockquote>}<p className={`text-sm mt-2 whitespace-pre-wrap break-words ${message.deleted_at?'italic text-gray-500':'text-gray-200'}`}>{message.body}</p><div className="flex gap-4 mt-3">{!message.deleted_at&&room.is_member&&!room.archived&&<button className="text-xs text-blue-300" disabled={busy} onClick={()=>setReply(message)}>Reply</button>}{message.can_edit&&<button className="text-xs text-blue-300" disabled={busy} onClick={()=>{setEditing(message);setEditBody(message.body);}}>Edit message</button>}{message.can_delete&&<button className="text-xs text-gray-400 hover:text-red-300" disabled={busy||loading} onClick={()=>setConfirmation(message.id)}>Delete message</button>}{!message.deleted_at&&<button className="text-xs text-gray-400" disabled={busy} onClick={()=>{setReport(message.id);setReason('');}}>Report message</button>}</div>{confirmation===message.id&&<div role="alertdialog" aria-label="Delete this message" className="mt-4 rounded-lg border border-red-500/40 p-3 space-y-3"><p className="text-sm text-gray-200">Delete this message for everyone in the room? A deleted-message placeholder remains so replies still make sense.</p>{error&&<p role="alert" className="text-sm text-red-300">{error}</p>}<div className="flex gap-3"><button autoFocus className="rounded-lg bg-red-600 px-3 py-2 text-sm text-white disabled:opacity-40" disabled={busy||loading} onClick={()=>void action(async()=>{await api.delete(`/study/rooms/${id}/messages/${message.id}`);if(editing?.id===message.id)setEditing(null);if(reply?.id===message.id)setReply(null);},'Message deleted.')}>{busy?'Deleting…':'Confirm delete'}</button><button className={secondary} disabled={busy} onClick={()=>setConfirmation(null)}>Cancel delete</button></div></div>}</article>)}
        {editing&&<form className="space-y-2" onSubmit={e=>{e.preventDefault();void action(async()=>{await api.patch(`/study/rooms/${id}/messages/${editing.id}`,{body:editBody});setEditing(null);},'Message edited.');}}><label className="text-sm text-gray-300">Edit your message<textarea aria-label="Edit your message" className={field} required maxLength={4000} value={editBody} onChange={e=>setEditBody(e.target.value)}/></label><button className={button} disabled={busy}>Save message</button><button type="button" className={secondary} onClick={()=>setEditing(null)}>Cancel editing</button></form>}
        {reply&&<div className="border-l-2 border-blue-400 pl-3 text-sm text-blue-200">Replying to {reply.author}: {reply.body.slice(0,160)} <button className="ml-3 underline" onClick={()=>setReply(null)}>Cancel reply</button></div>}
        {room.is_member && !room.archived && <form className="space-y-3 pt-3 border-t border-gray-700" onSubmit={e=>{e.preventDefault();void post();}}><label className="text-sm text-gray-300 block">Your message<textarea className={field} required maxLength={4000} rows={3} value={body} disabled={busy} onChange={e=>setBody(e.target.value)} placeholder="Ask a question, explain a concept, or plan the next study session."/></label><div className="flex justify-between items-center"><span className="text-xs text-gray-500">{body.length}/4000 · Shared with this room</span><button className={button} disabled={busy || loading || !body.trim()}>{busy?'Working…':'Post message'}</button></div></form>}
      </section>}
    </>}
  </div>;
}

export default function StudyTogetherPage(){
  const {id}=useParams();
  return id?<StudyRoomView key={id} id={id}/>:<RoomDirectory/>;
}
