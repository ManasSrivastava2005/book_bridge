import { useEffect, useState } from 'react';
import api from '../services/api';
type Level = { level: number; level_title: string; lifetime_xp: number; current_level_xp: number; xp_required_this_level: number; xp_remaining: number; progress_percent: number };
export default function ReaderLevelCard() {
  const [level, setLevel] = useState<Level | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => { let live = true; api.get('/xp/level').then(r => { if (live) setLevel(r.data); }).catch(() => { if (live) setError(true); }); return () => { live = false; }; }, []);
  return <section aria-label="Reader level" className="bb-panel p-5 text-body text-secondary">
    {!level ? <p role="status" className={error ? 'bb-meta' : 'bb-loading'}>{error ? 'Reader level is currently unavailable.' : 'Loading reader level…'}</p> : <>
      <h2 className="bb-card-title">Level {level.level} · {level.level_title}</h2>
      <p className="mt-2">{level.lifetime_xp.toLocaleString()} lifetime XP</p>
      <progress aria-label="Level progress" className="bb-progress my-3" value={level.progress_percent} max={100}/>
      <p>{level.current_level_xp} / {level.xp_required_this_level} XP · {level.xp_remaining === 0 && level.level === 50 ? 'Maximum level completed' : `${level.xp_remaining} XP to complete this level`}</p>
    </>}
  </section>;
}
