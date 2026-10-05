import StudentProgress from '../../components/StudentProgress';
import XPHistory from '../../components/XPHistory';
import AcademicProfileForm from '../../components/AcademicProfileForm';
import BadgeCollection from '../../components/BadgeCollection';
import ReaderLevelCard from '../../components/ReaderLevelCard';
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  User, Mail, Building, Bell, Shield, Key, Save, CheckCircle2,
  BookOpen, QrCode, Smartphone, Moon, Camera, Trash2, AlertCircle, Loader2
} from 'lucide-react';

export default function SettingsPage() {
  const { user, updateProfile, uploadAvatar, removeAvatar } = useAuth();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [studentId, setStudentId] = useState(user?.student_id || '');
  const [branch, setBranch] = useState(user?.branch || '');
  const [semester, setSemester] = useState(user?.semester ? `Semester ${user.semester}` : '');

  const [avatarPreview, setAvatarPreview] = useState<string | null>(user?.profile_image || null);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync state if user changes
  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setEmail(user.email || '');
      if (user.student_id) setStudentId(user.student_id);
      if (user.branch) setBranch(user.branch);
      if (user.semester) setSemester(`Semester ${user.semester}`);
      setAvatarPreview(user.profile_image || null);
    }
  }, [user]);

  // Notification Toggles
  const [notifyDueDate, setNotifyDueDate] = useState(true);
  const [notifyReservation, setNotifyReservation] = useState(true);
  const [notifyRecommendations, setNotifyRecommendations] = useState(true);
  const [notifyStreak, setNotifyStreak] = useState(false);

  // Handle avatar file selection
  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setErrorMessage('Image size must be less than 5MB');
      return;
    }

    setIsUploadingAvatar(true);
    setErrorMessage('');
    try {
      const newImageUrl = await uploadAvatar(file);
      setAvatarPreview(newImageUrl);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to upload profile picture');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  // Handle avatar removal
  const handleRemoveAvatar = async () => {
    setIsUploadingAvatar(true);
    setErrorMessage('');
    try {
      await removeAvatar();
      setAvatarPreview(null);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setErrorMessage('Failed to remove profile picture');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  // Handle profile form save
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setErrorMessage('');
    setSavedSuccess(false);

    try {
      const semNumber = parseInt(semester.replace('Semester ', ''), 10);
      await updateProfile({
        name: name.trim(),
        student_id: studentId.trim(),
        branch: branch.trim(),
        ...(Number.isFinite(semNumber) ? { semester: semNumber } : {}),
      });

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to update profile details. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const displayAvatar = avatarPreview
    ? avatarPreview.startsWith('http')
      ? avatarPreview
      : `${API_BASE}${avatarPreview}`
    : null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Header Banner */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <span className="px-3 py-0.5 rounded-full text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            Account & Academic Profile
          </span>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-2 flex items-center gap-2.5">
            <User className="w-7 h-7 text-blue-400" /> Student Profile & Settings
          </h1>
          <p className="text-gray-400 text-sm mt-1 max-w-xl">
            Update your student identity, manage your campus library card, and configure notifications.
          </p>
        </div>

        {/* Digital Library Card Badge */}
        <div className="bg-[#172033] border border-blue-500/30 p-4 rounded-xl flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
            <QrCode className="w-7 h-7" />
          </div>
          <div>
            <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Student ID</span>
            <p className="text-xs font-mono font-bold text-white">{studentId || 'Not provided'}</p>
            <span className="text-[10px] text-emerald-400 font-medium">Student profile</span>
          </div>
        </div>
      </div>

      <ReaderLevelCard />
      <StudentProgress />
      <XPHistory />
      <BadgeCollection />
      <AcademicProfileForm />


      {/* Status Messages */}
      {savedSuccess && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-400 text-sm font-medium animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>Profile changes have been successfully saved to the database and synchronized!</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-400 text-sm font-medium">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Profile Picture Section */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6">
        <h2 className="text-base font-bold text-white flex items-center gap-2 pb-4 border-b border-gray-800">
          <Camera className="w-4 h-4 text-blue-400" /> Profile Picture & Avatar
        </h2>

        <div className="flex flex-col sm:flex-row items-center gap-6 pt-4">
          <div className="relative group">
            {displayAvatar ? (
              <img
                src={displayAvatar}
                alt={name}
                className="w-24 h-24 rounded-2xl object-cover border-2 border-blue-500/40 shadow-lg"
              />
            ) : (
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center text-white text-3xl font-bold border-2 border-blue-500/40 shadow-lg">
                {name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
            )}
            {isUploadingAvatar && (
              <div className="absolute inset-0 bg-black/60 rounded-2xl flex items-center justify-center">
                <Loader2 className="w-6 h-6 text-white animate-spin" />
              </div>
            )}
          </div>

          <div className="space-y-2 text-center sm:text-left">
            <h3 className="text-sm font-semibold text-white">Upload New Photo</h3>
            <p className="text-xs text-gray-400">
              Supported formats: JPG, PNG, WebP. Maximum file size: 5MB.
            </p>
            <div className="flex items-center gap-3 pt-1 justify-center sm:justify-start">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleAvatarChange}
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAvatar}
                className="bg-[#1e293b] hover:bg-blue-600 text-white text-xs font-semibold px-4 py-2 rounded-xl transition flex items-center gap-1.5 border border-gray-700"
              >
                <Camera className="w-3.5 h-3.5" /> Choose Photo
              </button>

              {displayAvatar && (
                <button
                  type="button"
                  onClick={handleRemoveAvatar}
                  disabled={isUploadingAvatar}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-semibold px-3 py-2 rounded-xl transition flex items-center gap-1.5 border border-red-500/20"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Remove
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Profile Form */}
      <form onSubmit={handleSave} className="space-y-6">
        <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 space-y-5">
          <h2 className="text-base font-bold text-white flex items-center gap-2 pb-3 border-b border-gray-800">
            <User className="w-4 h-4 text-blue-400" /> Academic & Personal Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">Full Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">Institutional Email</label>
              <input
                type="email"
                value={email}
                disabled
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-xs text-gray-400 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">University Roll / Student ID</label>
              <input
                type="text"
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="e.g. 21BCSE042"
                className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">Department / Major Branch</label>
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="e.g. Computer Science & Engineering"
                className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">Current Semester</label>
              <select
                value={semester}
                onChange={(e) => setSemester(e.target.value)}
                className="w-full bg-[#172033] border border-gray-700/60 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
              >
                <option>Semester 1</option>
                <option>Semester 2</option>
                <option>Semester 3</option>
                <option>Semester 4</option>
                <option>Semester 5</option>
                <option>Semester 6</option>
                <option>Semester 7</option>
                <option>Semester 8</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1.5">Assigned Campus Library</label>
              <input
                type="text"
                value="Central University Library (MAIN)"
                disabled
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-3.5 py-2.5 text-xs text-blue-400 font-semibold cursor-not-allowed"
              />
            </div>
          </div>
        </div>

        {/* Notifications Card */}
        <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2 pb-3 border-b border-gray-800">
            <Bell className="w-4 h-4 text-blue-400" /> Notifications & Study Reminders
          </h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-xl bg-[#172033]/60 border border-gray-800">
              <div>
                <p className="text-xs font-semibold text-white">Book Due Date Warnings</p>
                <p className="text-[11px] text-gray-400">Receive alerts 3 days and 24 hours prior to borrow due dates</p>
              </div>
              <input
                type="checkbox"
                checked={notifyDueDate}
                onChange={(e) => setNotifyDueDate(e.target.checked)}
                className="w-4 h-4 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-[#172033]/60 border border-gray-800">
              <div>
                <p className="text-xs font-semibold text-white">Reservation Ready Alerts</p>
                <p className="text-[11px] text-gray-400">Instant notification when a reserved textbook is returned to the desk</p>
              </div>
              <input
                type="checkbox"
                checked={notifyReservation}
                onChange={(e) => setNotifyReservation(e.target.checked)}
                className="w-4 h-4 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-[#172033]/60 border border-gray-800">
              <div>
                <p className="text-xs font-semibold text-white">Curated AI Recommendations</p>
                <p className="text-[11px] text-gray-400">Weekly reading suggestions matching your semester syllabus milestones</p>
              </div>
              <input
                type="checkbox"
                checked={notifyRecommendations}
                onChange={(e) => setNotifyRecommendations(e.target.checked)}
                className="w-4 h-4 accent-blue-600 rounded"
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-[#172033]/60 border border-gray-800">
              <div>
                <p className="text-xs font-semibold text-white">Reading Streak Daily Check-in</p>
                <p className="text-[11px] text-gray-400">Daily reminder to maintain your reading streak for XP bonuses</p>
              </div>
              <input
                type="checkbox"
                checked={notifyStreak}
                onChange={(e) => setNotifyStreak(e.target.checked)}
                className="w-4 h-4 accent-blue-600 rounded"
              />
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs py-2.5 px-6 rounded-xl transition flex items-center gap-2 shadow-[0_0_12px_rgba(37,99,235,0.4)] disabled:opacity-50"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Saving Changes...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" /> Save Profile Details
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
