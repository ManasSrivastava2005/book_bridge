import AcademicFields, {emptyAcademic} from '../../components/AcademicFields';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { BookOpen, Mail, Lock, User, Eye, EyeOff } from 'lucide-react';

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [step,setStep] = useState(1);
  const [academic,setAcademic] = useState(emptyAcademic);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent, finish = false) => {
    e.preventDefault();
    if (step < 4 && !finish) { setStep(s=>s+1); return; }
    setError('');
    setLoading(true);
    try {
      await register(name, email, password, academic);
      navigate('/login');
    } catch (err: any) {
      setError(typeof err.response?.data?.detail === 'string' ? err.response.data.detail : 'Registration failed. Check your account and academic information.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex">
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-900/40 to-[#0a0e1a] items-center justify-center p-12">
        <div className="max-w-md text-center">
          <div className="w-20 h-20 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-8">
            <BookOpen className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">Book Bridge</h1>
          <p className="text-xl text-blue-300 mb-2">Read • Learn • Grow</p>
          <p className="text-gray-400">Join thousands of students who are transforming their learning experience.</p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="lg:hidden text-center mb-8">
            <div className="w-14 h-14 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <BookOpen className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Book Bridge</h1>
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">Create your account</h2>
          <p className="text-gray-400 mb-8">Start your reading journey today</p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 mb-6 text-red-400 text-sm">{error}</div>
          )}

          <p className="text-sm text-blue-300 mb-4">Step {step} of 4 · {['Account','Academic Information','Curriculum + Subjects','Optional Exams / Goals'][step-1]}</p>
          <form onSubmit={handleSubmit} className="space-y-5">
            <fieldset disabled={step!==1} className={step===1?'space-y-5':'hidden'}>
            <div>
              <label className="block text-sm text-gray-300 mb-2">Full Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your full name" required className="w-full bg-[#1a1f36] border border-gray-700/50 rounded-xl pl-11 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition" />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required className="w-full bg-[#1a1f36] border border-gray-700/50 rounded-xl pl-11 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition" />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Create a password" required minLength={6} className="w-full bg-[#1a1f36] border border-gray-700/50 rounded-xl pl-11 pr-12 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            </fieldset>
            {step>1 && <AcademicFields value={academic} onChange={setAcademic} step={step}/>}
            {step>1 && <div className="flex justify-between text-sm text-blue-300"><button type="button" onClick={()=>setStep(s=>s-1)}>Back</button><button type="button" disabled={loading} onClick={e=>void handleSubmit(e,true)}>Skip remaining setup and create account</button></div>}
            <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-semibold py-3 rounded-xl transition flex items-center justify-center gap-2">
              {loading ? <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-white"></div> : step<4?'Continue':'Create Account'}
            </button>
          </form>

          <p className="text-center text-gray-400 mt-6 text-sm">
            Already have an account? <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
