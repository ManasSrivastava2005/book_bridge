import ContributionPanel from '../../components/ContributionPanel';
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import { QuestionBank } from '../../types';
import {
  FileCheck, Search, Download, Filter, Calendar, BookOpen,
  Award, CheckCircle2, X, Plus, AlertCircle, HelpCircle
} from 'lucide-react';

export default function QuestionBanksPage() {
  const [questionBanks, setQuestionBanks] = useState<QuestionBank[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedExamType, setSelectedExamType] = useState('all');
  const [selectedSemester, setSelectedSemester] = useState('all');

  // Question details modal
  const [selectedQB, setSelectedQB] = useState<QuestionBank | null>(null);

  useEffect(() => {
    fetchQuestionBanks();
  }, [selectedExamType, selectedSemester]);

  const fetchQuestionBanks = async () => {
    setIsLoading(true);
    try {
      let url = '/question-banks/?';
      if (selectedExamType !== 'all') url += `exam_type=${selectedExamType}&`;
      if (selectedSemester !== 'all') url += `semester=${selectedSemester}&`;
      const res = await api.get(url);
      setQuestionBanks(res.data);
    } catch (err) {
      console.error('Failed to fetch question banks', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchQuestionBanks();
      return;
    }
    setIsLoading(true);
    api.get(`/question-banks/?search=${encodeURIComponent(searchQuery)}`)
      .then(res => setQuestionBanks(res.data))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  const [downloadError,setDownloadError]=useState('');
  const fileUrl=(value?:string)=>value?.startsWith('/uploads/')?`${api.defaults.baseURL}${value}`:value && /^https?:\/\//.test(value)?value:'#';
  const recordDownload=async(qb:QuestionBank)=>{if(!qb.file_url)return;try{const r=await api.post(`/question-banks/${qb.id}/download`);setQuestionBanks(items=>items.map(item=>item.id===qb.id?{...item,download_count:r.data.download_count}:item));setDownloadError('');}catch{setDownloadError('The file opened, but its download counter could not be updated.');}};
  const examTypes = ['all', 'End-Term', 'Mid-Term', 'Practice Set'];

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {downloadError && <p role="alert" className="text-red-300">{downloadError}</p>}
      {/* Top Banner */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="px-3 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            Exam Preparation & PYQs
          </span>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-2 flex items-center gap-2.5">
            <FileCheck className="w-7 h-7 text-amber-400" /> Question Banks & Past Examination Papers
          </h1>
          <p className="text-gray-400 text-sm mt-1 max-w-xl">
            Prepare for semester examinations with verified previous year question papers, mid-term tests, and solution rubrics.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-[#172033] border border-gray-800 rounded-xl px-4 py-2.5 text-center">
            <span className="text-[10px] text-gray-400 uppercase font-semibold block">Questions Solved</span>
            <span className="text-lg font-bold text-amber-400">100+ PYQs</span>
          </div>
        </div>
      </div>

      <details className="rounded-xl border border-slate-700 p-4"><summary className="cursor-pointer text-sm text-blue-300">Submit to Library — question papers and banks</summary><div className="mt-4"><ContributionPanel section="questions" /></div></details>

      {/* Search and Filters */}
      <div className="bg-[#111827]/60 border border-gray-800/60 rounded-2xl p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
        <form onSubmit={handleSearch} className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search exam papers by subject, year, or topic..."
            className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          <div className="flex flex-wrap gap-1.5">
            {examTypes.map((type) => (
              <button
                key={type}
                onClick={() => setSelectedExamType(type)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  selectedExamType === type
                    ? 'bg-amber-500 text-black font-semibold shadow'
                    : 'bg-[#172033] text-gray-300 hover:bg-gray-800'
                }`}
              >
                {type === 'all' ? 'All Exams' : type}
              </button>
            ))}
          </div>

          <select
            value={selectedSemester}
            onChange={(e) => setSelectedSemester(e.target.value)}
            className="bg-[#172033] border border-gray-700/60 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none"
          >
            <option value="all">All Semesters</option>
            <option value="3">Semester 3</option>
            <option value="4">Semester 4</option>
            <option value="5">Semester 5</option>
            <option value="6">Semester 6</option>
          </select>
        </div>
      </div>

      {/* Question Banks Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-gray-500 text-sm">Loading exam question banks...</div>
      ) : questionBanks.length === 0 ? (
        <div className="py-20 text-center text-gray-500 text-sm bg-[#111827]/40 rounded-2xl border border-gray-800/40">
          <FileCheck className="w-10 h-10 mx-auto text-gray-600 mb-2" />
          No question banks found for the selected criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {questionBanks.map((qb) => (
            <div
              key={qb.id}
              className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-5 flex flex-col justify-between hover:border-amber-500/40 transition group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="px-2.5 py-0.5 rounded-md text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    {qb.exam_type} • {qb.academic_year}
                  </span>
                  <span className="text-[10px] text-gray-500">
                    Semester {qb.semester}
                  </span>
                </div>

                <h3 className="text-white font-bold text-sm line-clamp-2 group-hover:text-amber-400 transition">
                  {qb.title}
                </h3>
                <p className="text-xs text-gray-400 line-clamp-2 mt-2 leading-relaxed">
                  {qb.description || 'Verified past question paper with question breakdowns and marking guidelines.'}
                </p>

                <div className="flex items-center gap-3 mt-4 text-[11px] text-gray-400">
                  <span className="bg-[#172033] px-2 py-0.5 rounded text-gray-300 font-medium">
                    {qb.subject}
                  </span>
                  <span>{qb.total_questions} Questions</span>
                  <span>{qb.download_count} Downloads</span>
                </div>
              </div>

              <div className="mt-5 pt-3.5 border-t border-gray-800/80 flex items-center gap-2">
                <button
                  onClick={() => setSelectedQB(qb)}
                  className="flex-1 bg-[#1e293b] hover:bg-gray-700 text-white text-xs font-semibold py-2 rounded-xl transition flex items-center justify-center gap-1.5"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-amber-400" /> View Details
                </button>
                <a
                  href={fileUrl(qb.file_url)}
                  onClick={()=>void recordDownload(qb)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-amber-500 hover:bg-amber-600 text-black text-xs font-bold px-3 py-2 rounded-xl transition flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" /> PDF
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Details Modal */}
      {selectedQB && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#111827] border border-gray-800 rounded-2xl max-w-lg w-full p-6 space-y-4 animate-scaleIn">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800">
              <h3 className="font-bold text-white text-base truncate">{selectedQB.title}</h3>
              <button onClick={() => setSelectedQB(null)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-[#172033] p-3 rounded-xl border border-gray-800">
                <div><span className="text-gray-400">Subject:</span> <span className="text-white font-semibold">{selectedQB.subject}</span></div>
                <div><span className="text-gray-400">Semester:</span> <span className="text-white font-semibold">Semester {selectedQB.semester}</span></div>
                <div><span className="text-gray-400">Exam Type:</span> <span className="text-amber-400 font-semibold">{selectedQB.exam_type}</span></div>
                <div><span className="text-gray-400">Academic Year:</span> <span className="text-white font-semibold">{selectedQB.academic_year}</span></div>
              </div>

              <div>
                <span className="text-gray-400 block mb-1 font-semibold">Exam Description & Syllabus Coverage:</span>
                <p className="text-gray-300 bg-[#172033] p-3 rounded-xl leading-relaxed border border-gray-800">
                  {selectedQB.description}
                </p>
              </div>

              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-2 text-amber-300">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-amber-400" />
                <span>Contains {selectedQB.total_questions} verified practice problems with solution keys.</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-800">
              <button
                onClick={() => setSelectedQB(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white"
              >
                Close
              </button>
              <a
                href={fileUrl(selectedQB.file_url)}
                onClick={()=>void recordDownload(selectedQB)}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-amber-500 hover:bg-amber-600 text-black text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" /> Download Examination Paper
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
