import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import api from '../services/api';
type Rooms={joined_count:number;items:{id:number;title:string;new_messages:number;latest_activity:string}[]};
export default function StudyRoomsSummary(){
 const [data,setData]=useState<Rooms|null>(null),[error,setError]=useState(false);
 useEffect(()=>{let live=true;const load=()=>{if(document.hidden)return;api.get('/study/dashboard/rooms').then(r=>{if(live){setData(r.data);setError(false);}}).catch(()=>{if(live)setError(true);});};load();const timer=window.setInterval(load,30000);window.addEventListener('focus',load);return()=>{live=false;clearInterval(timer);window.removeEventListener('focus',load);};},[]);
 return <section className="bb-panel p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="bb-card-title">Your study rooms</h2><Link to="/study-together" className="text-meta text-blue-300 hover:text-blue-200">Browse rooms →</Link></div>{error?<p className="bb-meta mt-2">Room activity is temporarily unavailable.</p>:data?<><p className="bb-meta mt-2">{data.joined_count} joined · updates every 30 seconds</p>{data.items.map(r=><Link key={r.id} to={`/study-together/${r.id}`} className="block border-t border-line mt-4 pt-4 text-body text-blue-200 hover:text-ink">{r.title}<span className="block bb-meta">{r.new_messages?`${r.new_messages} new messages since your last visit`:'No new messages'} · {new Date(r.latest_activity).toLocaleDateString()}</span></Link>)}{!data.items.length&&<p className="bb-meta mt-3">Join a topic room to discuss what you are learning.</p>}</>:<p className="bb-meta mt-2">Loading rooms…</p>}</section>;
}
