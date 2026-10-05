import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { DigitalResource } from '../../types';
import {
  Globe, Search, BookOpen, ExternalLink, Filter, ShieldCheck,
  CheckCircle2, Sparkles, BookMarked, Download, FileText
} from 'lucide-react';

export default function DigitalResourcesPage() {
  const [resources, setResources] = useState<DigitalResource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    fetchResources();
  }, [selectedType]);

  const fetchResources = async () => {
    setIsLoading(true);
    try {
      let url = '/digital-resources/?';
      if (selectedType !== 'all') url += `resource_type=${selectedType}&`;
      const res = await api.get(url);
      setResources(res.data);
    } catch (err) {
      console.error('Failed to fetch digital resources', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      fetchResources();
      return;
    }
    setIsLoading(true);
    api.get(`/digital-resources/?search=${encodeURIComponent(searchQuery)}`)
      .then(res => setResources(res.data))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12">
      {/* Top Banner */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="px-3 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
            Digital Library & E-Books
          </span>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-2 flex items-center gap-2.5">
            <Globe className="w-7 h-7 text-cyan-400" /> Curated Digital Library
          </h1>
          <p className="text-gray-400 text-sm mt-1 max-w-xl">
            Explore verified open-access textbooks, university curated technical guides, and embedded online reading.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="bg-[#172033] border border-cyan-500/30 rounded-xl px-4 py-2.5 text-center">
            <span className="text-[10px] text-gray-400 uppercase font-semibold block">Open Access</span>
            <span className="text-lg font-bold text-cyan-400">Staff reviewed</span>
          </div>
        </div>
      </div>

      {/* Tabs & Search */}
      <div className="bg-[#111827]/60 border border-gray-800/60 rounded-2xl p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
        {/* Search */}
        <form onSubmit={handleSearch} className="relative w-full md:max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search e-books by title, author, or subject..."
            className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
        </form>

        {/* Category Tabs */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {[
            { id: 'all', label: 'All Digital Resources' },
            { id: 'open_access', label: 'Free Open Access' },
            { id: 'uploaded_pdf', label: 'Campus Curated PDFs' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedType(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                selectedType === tab.id
                  ? 'bg-cyan-600 text-white shadow'
                  : 'bg-[#172033] text-gray-300 hover:bg-gray-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Resources Cards Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-gray-500 text-sm">Loading online e-books...</div>
      ) : resources.length === 0 ? (
        <div className="py-20 text-center text-gray-500 text-sm bg-[#111827]/40 rounded-2xl border border-gray-800/40">
          <BookOpen className="w-10 h-10 mx-auto text-gray-600 mb-2" />
          No digital resources found.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {resources.map((res) => (
            <div
              key={res.id}
              className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-4 flex flex-col justify-between hover:border-cyan-500/40 transition group"
            >
              <div>
                {/* Cover Image */}
                <div className="relative w-full h-48 rounded-xl overflow-hidden bg-gray-900 mb-3">
                  <img
                    src={(res.cover_image?.startsWith('/uploads/')?`${api.defaults.baseURL}${res.cover_image}`:res.cover_image) || 'https://images.unsplash.com/photo-1532012164546-f432f2e3d93c?w=400&q=80'}
                    alt={res.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-70" />
                  <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-cyan-900/80 backdrop-blur-sm text-cyan-300 text-[10px] font-bold border border-cyan-500/30">
                    {res.provider}
                  </span>
                </div>

                <h3 className="text-white font-bold text-sm line-clamp-1 group-hover:text-cyan-400 transition">
                  {res.title}
                </h3>
                <p className="text-xs text-gray-400 line-clamp-1 mt-0.5">{res.author}</p>

                <p className="text-xs text-gray-400 line-clamp-2 mt-2 leading-relaxed">
                  {res.description || 'Verified academic resource available for open online reading.'}
                </p>

                <div className="flex flex-wrap gap-1.5 mt-3">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-medium">
                    {res.subject || 'CS'}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-900/30 text-emerald-400 border border-emerald-700/30 font-medium">
                    {res.license_name || 'Open Access'}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-800/80 flex items-center gap-2">
                <Link
                  to={`/reader/${res.id}`}
                  className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white text-xs font-semibold py-2 rounded-xl transition flex items-center justify-center gap-1.5 shadow-[0_0_10px_rgba(6,182,212,0.3)]"
                >
                  <BookOpen className="w-3.5 h-3.5" /> Read Online
                </Link>

                {res.external_url && (
                  <a
                    href={res.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-[#1e293b] hover:bg-gray-700 text-gray-300 hover:text-white p-2 rounded-xl transition"
                    title="External Provider Link"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
