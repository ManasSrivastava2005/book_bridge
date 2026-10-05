import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import api from '../services/api';
type Badge = { id:number; name:string; description:string; earned:boolean };
export default function BadgeCollection({earnedOnly=false}:{earnedOnly?:boolean}) {
 const [badges,setBadges]=useState<Badge[]|null>(null),[error,setError]=useState(false);
 useEffect(()=>{let live=true;api.get('/badges/my').then(r=>{if(live)setBadges(r.data);}).catch(()=>{if(live)setError(true);});return()=>{live=false;};},[]);
 const visible=badges?.filter(b=>!earnedOnly || b.earned);
 return <section aria-label="Badge collection" className="rounded-xl border border-slate-700 bg-slate-900 p-4"><Link to="/achievements" className="float-right text-sm text-blue-300">View achievements →</Link><h2 className="font-bold text-white">{earnedOnly?'Earned badges':'Badge collection'}</h2>{!badges?<p role="status" className="text-sm text-slate-400">{error?'Badges are currently unavailable.':'Loading badges…'}</p>:<><p className="text-xs text-slate-400 mt-2">{badges.filter(b=>b.earned).length} earned</p><div className="grid sm:grid-cols-2 gap-2 mt-3">{visible?.map(b=><div key={b.id} className={`rounded-lg border p-3 ${b.earned?'border-amber-400/40 text-amber-200':'border-slate-700 text-slate-500'}`}><p className="text-sm font-semibold">{b.name} · {b.earned?'Earned':'Locked'}</p><p className="text-xs mt-1">{b.description}</p></div>)}</div>{!visible?.length&&<p className="text-sm text-slate-400">No badges earned yet.</p>}</>}</section>;
}
