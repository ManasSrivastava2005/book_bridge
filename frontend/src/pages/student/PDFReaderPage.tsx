import { lazy, Suspense, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';
import api from '../../services/api';
import type { DigitalResource } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { libraryError } from '../../utils/library';
import { readerUrl } from '../../utils/reader';
const PdfWorkspace=lazy(()=>import('../../components/PdfWorkspace'));
const control='rounded-xl border border-gray-700 bg-[#172033] px-3 py-2 text-sm text-gray-200 hover:bg-gray-700';

export default function PDFReaderPage() {
  const {id}=useParams<{id:string}>();
  const {user,token}=useAuth();
  return <ReaderDocument key={`${user?.id}:${id}`} id={id} userId={user?.id} token={token || undefined} />;
}
function ReaderDocument({id,userId,token}:{id?:string;userId?:number;token?:string}) {
  const {user}=useAuth();
  const back=user?.role === "student" ? "/resources" : "/admin/resources";
  const [resource,setResource]=useState<DigitalResource|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [downloadError,setDownloadError]=useState('');
  const [downloading,setDownloading]=useState(false);
  useEffect(()=>{
    let active=true;
    if(!id || !/^\d+$/.test(id)){setError('Invalid digital resource.');setLoading(false);return;}
    api.get(`/digital-resources/${id}`).then(response=>{if(active)setResource(response.data);}).catch(reason=>{if(active)setError(libraryError(reason,'This resource could not be opened.'));}).finally(()=>{if(active)setLoading(false);});
    return()=>{active=false;};
  },[id]);
  if(loading)return <div className="py-20 text-gray-400 flex justify-center gap-3"><Loader2 className="animate-spin" />Loading reader…</div>;
  if(!resource || error)return <div className="py-20 text-center space-y-4"><p role="alert" className="text-red-300">{error || 'Digital resource not found.'}</p><Link className="text-cyan-400" to={back}>Back to Digital Library</Link></div>;
  const base=String(api.defaults.baseURL || window.location.origin);
  const url=readerUrl(resource.file_url,base) || readerUrl(resource.external_url,base);
  const managed=!!resource.file_url?.match(/^\/digital-resources\/files\/[a-f0-9]{32}\.pdf$/);
  const protectedFile=managed || !!resource.file_url?.startsWith('/uploads/');
  const download=async()=>{setDownloading(true);setDownloadError('');try{const response=await api.get(resource.file_url!,{params:{download:true},responseType:'blob'});const blob=URL.createObjectURL(response.data);const link=document.createElement('a');link.href=blob;link.download='book.pdf';link.click();window.setTimeout(()=>URL.revokeObjectURL(blob),1000);}catch{setDownloadError('Unable to download this PDF. Check your access or contact the librarian.');}finally{setDownloading(false);}};
  const isPdf=!!url && (resource.resource_type==='uploaded_pdf' || /\.pdf$/i.test(new URL(url).pathname));
  return <div className="max-w-[1800px] mx-auto space-y-3 pb-6">
    <header className="rounded-2xl border border-gray-800 bg-[#111827] p-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3 min-w-0"><Link to={back} aria-label="Back to Digital Library" className={control}><ArrowLeft size={18}/></Link><div className="min-w-0"><h1 className="text-white font-bold break-words">{resource.title}</h1><p className="text-xs text-gray-400">{resource.author} · {resource.provider}</p></div></div>
      <div className="flex flex-wrap gap-2 items-center">{resource.license_name && <span className="text-xs text-emerald-400">{resource.license_name}</span>}{protectedFile && resource.download_allowed && <button className={control} disabled={downloading} onClick={()=>void download()}>{downloading?'Downloading…':'Download PDF'}</button>}{url && !protectedFile && <a href={url} target="_blank" rel="noopener noreferrer" className={control}><ExternalLink size={14} className="inline mr-2"/>Open original</a>}</div>
    </header>
    {downloadError && <p role="alert" className="text-red-300 text-sm">{downloadError}</p>}
    {!url ? <div role="alert" className="p-10 border border-gray-800 rounded-2xl text-gray-300">This resource has no readable file or supported web link. Please contact your librarian.</div> : isPdf && userId ? <Suspense fallback={<p className="text-gray-400">Loading PDF tools…</p>}><PdfWorkspace url={url} resourceId={resource.id} userId={userId} token={protectedFile?token:undefined}/></Suspense> : <section className="rounded-2xl overflow-hidden border border-gray-800"><iframe src={url} title={resource.title} className="w-full h-[70vh] min-h-[400px] border-0"/><p className="p-3 text-xs text-gray-400">If the provider prevents embedded reading, use Open original. Synced page tools are available for PDFs.</p></section>}
  </div>;
}
