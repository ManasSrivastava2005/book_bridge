import { useState } from 'react';
import api from '../services/api';
import { libraryError } from '../utils/library';
export type CurriculumNodeDraft={id:number|null;title:string;code:string|null;objectives:string|null;subtopics:string[];children:CurriculumNodeDraft[]};
export type CurriculumDraft={semester?:number;curriculum_id:number|null;expected_version:number;title:string;subjects:CurriculumNodeDraft[]};
export const emptyNode=():CurriculumNodeDraft=>({id:null,title:'',code:null,objectives:null,subtopics:[],children:[]});
const field='w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm text-white';
const button='rounded-lg border border-slate-700 px-3 py-2 text-sm text-blue-200 disabled:opacity-40';

export function NodeEditor({node,depth,onChange,onRemove,disabled,hideRemove=false}:{node:CurriculumNodeDraft;depth:number;onChange:(node:CurriculumNodeDraft)=>void;onRemove:()=>void;disabled:boolean;hideRemove?:boolean}){
 const label=['Subject','Unit','Topic'][depth];
 return <fieldset disabled={disabled} className="border border-slate-700 rounded-xl p-3 space-y-3"><legend className="px-2 text-blue-200 text-sm">{label}</legend>
  <div className="flex gap-2 items-end"><label className="grow text-sm text-slate-300">{label} title<input className={field} required maxLength={200} value={node.title} onChange={e=>onChange({...node,title:e.target.value})}/></label>{!hideRemove&&<button type="button" className={button} onClick={onRemove}>Remove {label.toLowerCase()}</button>}</div>
  {depth===0 && <label className="block text-sm text-slate-300">Course code<input className={field} maxLength={50} value={node.code || ''} onChange={e=>onChange({...node,code:e.target.value || null})}/></label>}
  <label className="block text-sm text-slate-300">{label} objectives<textarea className={field} maxLength={2000} value={node.objectives || ''} onChange={e=>onChange({...node,objectives:e.target.value || null})}/></label>
  {depth===2 && <label className="block text-sm text-slate-300">Subtopics (one per line)<textarea className={field} value={node.subtopics.join('\n')} onChange={e=>onChange({...node,subtopics:e.target.value.split('\n')})}/></label>}
  {node.children.map((child,index)=><NodeEditor key={child.id || `new-${index}`} node={child} depth={depth+1} disabled={disabled} onChange={value=>onChange({...node,children:node.children.map((n,i)=>i===index?value:n)})} onRemove={()=>onChange({...node,children:node.children.filter((_,i)=>i!==index)})}/>)}
  {depth<2 && <button type="button" className={button} onClick={()=>onChange({...node,children:[...node.children,emptyNode()]})}>Add {depth===0?'unit':'topic'}</button>}
 </fieldset>;
}

export function CurriculumTreeForm({draft,onChange,busy,onSubmit,submitLabel='Confirm curriculum'}:{draft:CurriculumDraft;onChange:(value:CurriculumDraft)=>void;busy:boolean;onSubmit:()=>void;submitLabel?:string}){
 return <form className="space-y-4" onSubmit={e=>{e.preventDefault();onSubmit();}}>
  <label className="block text-sm text-slate-300">Curriculum title<input required className={field} maxLength={200} value={draft.title} disabled={busy} onChange={e=>onChange({...draft,title:e.target.value})}/></label>
  {draft.subjects.map((subject,index)=><NodeEditor key={subject.id || `new-${index}`} node={subject} depth={0} disabled={busy} onChange={value=>onChange({...draft,subjects:draft.subjects.map((s,i)=>i===index?value:s)})} onRemove={()=>onChange({...draft,subjects:draft.subjects.filter((_,i)=>i!==index)})}/>)}
  <button type="button" className={button} disabled={busy} onClick={()=>onChange({...draft,subjects:[...draft.subjects,emptyNode()]})}>Add subject</button>
  <p className="text-xs text-slate-400">Confirmation makes this your selected personal curriculum. Removed items leave the active plan; their saved progress, exams and history are retained.</p>
  <button className="rounded-xl bg-blue-600 px-4 py-2 text-white disabled:opacity-40" disabled={busy}>{busy?'Saving…':submitLabel}</button>
 </form>;
}

export function cleanCurriculum(draft:CurriculumDraft):CurriculumDraft{
 const clean=(nodes:CurriculumNodeDraft[]):CurriculumNodeDraft[]=>nodes.map(n=>({...n,subtopics:n.subtopics.map(s=>s.trim()).filter(Boolean),children:clean(n.children)}));
 return {...draft,subjects:clean(draft.subjects)};
}

export default function PersonalCurriculumEditor({onSaved}:{onSaved:()=>void}){
 const [draft,setDraft]=useState<CurriculumDraft|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const open=async(semester?:number)=>{setBusy(true);setError('');setNotice('');try{setDraft((await api.get('/academic/personal-curriculum',{params:{semester}})).data);}catch(e){setError(libraryError(e,'Could not load personal curriculum.'));}finally{setBusy(false);}};
 const save=async()=>{if(!draft)return;setBusy(true);setError('');try{setDraft((await api.put('/academic/personal-curriculum',cleanCurriculum(draft))).data);setNotice('Personal curriculum confirmed. Learning Path now use these subjects.');onSaved();}catch(e){setError(libraryError(e,'Could not save curriculum. Reload if another session changed it.'));}finally{setBusy(false);}};
 return <section className="rounded-xl border border-slate-800 bg-[#111827] p-5 space-y-4"><div className="flex flex-wrap gap-3 justify-between"><h2 className="font-semibold text-white">Manage my subjects and curriculum</h2><button className={button} disabled={busy} onClick={()=>void open()}>{draft?'Reload saved curriculum':'Create or edit personal curriculum'}</button></div><p className="text-sm text-slate-400">Build your own subjects, units and topics. Your personal curriculum is available only in your student account.</p>{error && <p role="alert" className="text-red-300">{error}</p>}{notice && <p role="status" className="text-emerald-300">{notice}</p>}{draft && <><label className="block text-sm text-slate-300">Semester to view or edit<select aria-label="Curriculum semester" className={field} value={draft.semester || 1} disabled={busy} onChange={e=>{if(window.confirm('Switch semester? Unsaved edits will be discarded.'))void open(Number(e.target.value));}}>{Array.from({length:20},(_,i)=><option key={i+1} value={i+1}>Semester {i+1}</option>)}</select></label><p className="text-xs text-slate-400">Each semester retains its own subjects and progress. Saving activates this semester for your Learning Path.</p>{draft.curriculum_id && <button type="button" className={button} disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await api.post(`/academic/personal-curriculum/semesters/${draft.semester}/activate`);setNotice(`Semester ${draft.semester} is now active.`);onSaved();}catch(e){setError(libraryError(e,'Could not activate semester.'));}finally{setBusy(false);}}}>Use semester {draft.semester}</button>}<CurriculumTreeForm draft={draft} onChange={setDraft} busy={busy} onSubmit={()=>void save()}/></>}</section>;
}
