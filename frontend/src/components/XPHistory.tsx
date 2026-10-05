import {useEffect,useState} from 'react';
import api from '../services/api';
type History={total:number;items:{id:number;amount:number;description:string;created_at:string}[]};
export default function XPHistory(){
 const [page,setPage]=useState(1),[data,setData]=useState<History|null>(null),[error,setError]=useState(false);
 useEffect(()=>{let live=true;setData(null);setError(false);api.get('/xp/history',{params:{page,page_size:10}}).then(r=>{if(live)setData(r.data);}).catch(()=>{if(live)setError(true);});return()=>{live=false;};},[page]);
 return <section className="bb-panel p-5 space-y-4 text-body text-secondary"><h2 className="bb-card-title">XP history</h2>{error?<p role="status">XP history could not be loaded.</p>:!data?<p role="status">Loading XP history…</p>:<><ul className="divide-y divide-line">{data.items.map(r=><li key={r.id} className="py-3 flex justify-between gap-4"><div>{r.description}<p className="bb-meta mt-1">{new Date(r.created_at).toLocaleString()}</p></div><span className="shrink-0 tabular-nums text-emerald-300">+{r.amount} XP</span></li>)}</ul>{!data.total&&<p>No XP earned yet.</p>}<div className="flex flex-wrap items-center justify-between gap-3"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="bb-button bb-button-secondary">Previous</button><span>Page {page}</span><button disabled={page*10>=data.total} onClick={()=>setPage(p=>p+1)} className="bb-button bb-button-secondary">Next</button></div></>}</section>;
}
