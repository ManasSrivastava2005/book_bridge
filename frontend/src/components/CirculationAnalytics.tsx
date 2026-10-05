import { useEffect, useState } from 'react';
import api from '../services/api';
import type { Library } from '../types';
import { libraryError } from '../utils/library';

interface Analytics {
  period: { days: number; start: string; end: string; as_of: string; library_id: number | null };
  totals: { checkouts: number; returns: number; unique_borrowers: number };
  daily: { date: string; checkouts: number; returns: number }[];
  categories: { category: string; checkouts: number }[];
  overdue: { label: string; count: number }[];
}
const control = 'rounded-xl border border-gray-700 bg-[#172033] px-3 py-2 text-sm text-white disabled:opacity-40';

export default function CirculationAnalytics() {
  const [days, setDays] = useState('30');
  const [library, setLibrary] = useState('');
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    Promise.all([
      api.get<Analytics>('/admin/analytics', { params: { days: Number(days), library_id: library || undefined } }),
      api.get<Library[]>('/libraries/'),
    ]).then(([analytics, branches]) => {
      if (active) { setData(analytics.data); setLibraries(branches.data); }
    }).catch(e => {
      if (active) setError(libraryError(e, 'Could not load circulation analytics.'));
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [days, library, attempt]);

  const exportCsv = () => {
    if (!data || loading || error) return;
    const rows = ['Date,Checkouts,Returns', ...data.daily.map(row => `${row.date},${row.checkouts},${row.returns}`)];
    const url = URL.createObjectURL(new Blob(['\uFEFF' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `circulation-${data.period.library_id ?? 'all'}-${data.period.start}-${data.period.end}.csv`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const maximum = Math.max(1, ...data?.daily.flatMap(row => [row.checkouts, row.returns]) || []);

  return <section aria-labelledby="circulation-analytics-title" className="bg-[#111827] border border-gray-800 rounded-2xl p-5 space-y-5">
    <div className="flex flex-wrap justify-between gap-3">
      <div><h2 id="circulation-analytics-title" className="text-white font-semibold">Circulation analytics</h2>
        <p className="text-xs text-gray-400 mt-1">Recorded checkouts and returns by calendar day, including today. Dates use the database time zone.</p></div>
      <div className="flex flex-wrap gap-2 items-end">
        <label className="text-xs text-gray-400">Period<select aria-label="Analytics period" className={`${control} block mt-1`} value={days} onChange={e => setDays(e.target.value)}>
          <option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option>
        </select></label>
        <label className="text-xs text-gray-400">Library<select aria-label="Analytics library" className={`${control} block mt-1 max-w-full`} value={library} onChange={e => setLibrary(e.target.value)}>
          <option value="">All libraries</option>{libraries.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
        <button className={control} onClick={() => setAttempt(value => value + 1)} disabled={loading}>Refresh analytics</button>
        <button className={control} onClick={exportCsv} disabled={loading || !!error || !data}>Export daily CSV</button>
      </div>
    </div>
    {loading ? <p role="status" className="text-gray-400 text-sm">Loading circulation analytics…</p> : error ?
      <div role="alert" className="text-red-300 text-sm">{error} <button className="underline" onClick={() => setAttempt(value => value + 1)}>Retry analytics</button></div> : data && <>
        <p className="text-xs text-gray-500">{data.period.start} – {data.period.end} · Updated {data.period.as_of.replace('T', ' ').slice(0, 19)} · Filters apply to this analytics section.</p>
        <div className="grid sm:grid-cols-3 gap-3">{[
          ['Checkouts in period', data.totals.checkouts], ['Returns in period', data.totals.returns], ['Borrowers in period', data.totals.unique_borrowers],
        ].map(([label, value]) => <div key={label} className="rounded-xl bg-[#172033] p-3"><p className="text-xs text-gray-400">{label}</p><p className="text-xl font-semibold text-white mt-1">{value}</p></div>)}</div>
        <div>
          <p className="text-xs text-gray-400 mb-2"><span className="text-blue-400">Blue: checkouts</span> · <span className="text-teal-400">Teal: returns</span></p>
          <div role="img" aria-label={`Daily circulation: ${data.totals.checkouts} checkouts and ${data.totals.returns} returns. Exact daily values are available in the table below.`} className="flex items-end gap-1 h-32 border-b border-gray-700">
            {data.daily.map(row => <div key={row.date} title={`${row.date}: ${row.checkouts} checkouts, ${row.returns} returns`} className="flex items-end gap-px flex-1 h-full min-w-0">
              <div className="flex-1 bg-blue-500 rounded-t" style={{ height: `${row.checkouts / maximum * 100}%` }} />
              <div className="flex-1 bg-teal-400 rounded-t" style={{ height: `${row.returns / maximum * 100}%` }} />
            </div>)}
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1"><span>{data.period.start}</span><span>{data.period.end}</span></div>
          {!data.totals.checkouts && !data.totals.returns && <p className="text-sm text-gray-400 mt-2">No circulation activity recorded for this period and library.</p>}
          <details className="mt-3 text-sm text-gray-300"><summary className="cursor-pointer">Daily activity table</summary>
            <div className="max-h-64 overflow-auto mt-2"><table className="w-full text-left text-xs"><caption className="sr-only">Daily checkout and return counts</caption>
              <thead><tr><th className="py-2">Date</th><th>Checkouts</th><th>Returns</th></tr></thead>
              <tbody>{data.daily.map(row => <tr key={row.date} className="border-t border-gray-800"><th className="py-2 font-normal">{row.date}</th><td>{row.checkouts}</td><td>{row.returns}</td></tr>)}</tbody>
            </table></div>
          </details>
        </div>
        <div className="grid md:grid-cols-2 gap-5">
          <div><h3 className="text-sm text-white font-medium">Current overdue ages</h3><p className="text-xs text-gray-500 mt-1">Outstanding loans now, regardless of selected period. Library filter applies.</p>
            <ul className="mt-2 divide-y divide-gray-800">{data.overdue.map(row => <li key={row.label} className="py-2 flex justify-between text-sm text-gray-300"><span>{row.label}</span><span className="text-amber-300">{row.count}</span></li>)}</ul>
          </div>
          <div><h3 className="text-sm text-white font-medium">Most borrowed categories</h3><p className="text-xs text-gray-500 mt-1">Up to eight categories ranked by checkouts in this period.</p>
            <ul className="mt-2 divide-y divide-gray-800">{data.categories.map(row => <li key={row.category} className="py-2 flex justify-between gap-2 text-sm text-gray-300"><span className="break-words min-w-0">{row.category}</span><span>{row.checkouts}</span></li>)}</ul>
            {!data.categories.length && <p className="text-sm text-gray-500 mt-2">No checkouts in this period.</p>}
          </div>
        </div>
      </>}
  </section>;
}
