import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { useEffect,useState } from 'react';
import api from '../services/api';
import AcademicFields,{AcademicValue,emptyAcademic} from './AcademicFields';
export default function AcademicProfileForm(){
 const {refreshUser}=useAuth();
 const [value,setValue]=useState<AcademicValue>(emptyAcademic),[loaded,setLoaded]=useState(false),[message,setMessage]=useState(''),[saving,setSaving]=useState(false);
 useEffect(()=>{api.get('/academic/profile').then(r=>{setValue(r.data);setLoaded(true);}).catch(()=>setMessage('Academic profile could not be loaded.'));},[]);
 return <section className="rounded-2xl border border-slate-800 bg-[#111827] p-6 space-y-4"><h2 className="font-bold text-white">Academic information</h2><Link to="/curriculum" className="text-blue-300 text-sm">Open My Curriculum</Link>{message&&<p role="status" className="text-sm text-blue-200">{message}</p>}{loaded?<form className="space-y-4" onSubmit={async e=>{e.preventDefault();setSaving(true);try{const r=await api.put('/academic/profile',value);setValue(r.data);await refreshUser();window.dispatchEvent(new Event('academic-profile-updated'));setMessage('Academic information saved.');}catch{setMessage('Could not save academic information. Check the selected curriculum and subjects.');}finally{setSaving(false);}}}><AcademicFields value={value} onChange={setValue}/><button disabled={saving} className="rounded-lg bg-blue-600 px-4 py-2 text-white">{saving?'Saving…':'Save academic information'}</button></form>:<p className="text-slate-400">Loading academic information…</p>}</section>;
}
