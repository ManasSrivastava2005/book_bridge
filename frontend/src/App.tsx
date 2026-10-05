import AchievementsPage from './pages/student/AchievementsPage';
import StaffProfilePage from './pages/librarian/StaffProfilePage';
import StudentCurriculumPage from './pages/student/CurriculumPage';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import StudentLayout from './layouts/StudentLayout';
import QRManagementPage from './pages/librarian/QRManagementPage';
import AnalyticsPage from './pages/librarian/AnalyticsPage';
import AnnouncementsPage from './pages/librarian/AnnouncementsPage';
import StudentDataPage from './pages/librarian/StudentDataPage';
import QuizManagementPage from './pages/librarian/QuizManagementPage';
import ContributionsPage from './pages/librarian/ContributionsPage';
import StaffLayout from './layouts/StaffLayout';
import StaffLoginPage from './pages/auth/StaffLoginPage';

// Pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/student/DashboardPage';
import BrowseBooksPage from './pages/student/BrowseBooksPage';
import BookDetailsPage from './pages/student/BookDetailsPage';
import MyBooksPage from './pages/student/MyBooksPage';
import LibrarianDashboardPage from './pages/librarian/LibrarianDashboardPage';
import BookManagementPage from './pages/librarian/BookManagementPage';
import StudyModerationPage from './pages/librarian/StudyModerationPage';
import CirculationPage from './pages/librarian/CirculationPage';
import DigitalResourceManagementPage from './pages/librarian/DigitalResourceManagementPage';

import AIAssistantPage from './pages/student/AIAssistantPage';
import LearningPathPage from './pages/student/LearningPathPage';
import RecommendationsPage from './pages/student/RecommendationsPage';
import LeaderboardPage from './pages/student/LeaderboardPage';
import QuizzesPage from './pages/student/QuizzesPage';
import SettingsPage from './pages/student/SettingsPage';
import ScanPage from './pages/student/ScanPage';

// New Academic & Digital Resource Pages
import NotificationsPage from './pages/student/NotificationsPage';
import StudyTogetherPage from './pages/student/StudyTogetherPage';
import NotesPage from './pages/student/NotesPage';
import QuestionBanksPage from './pages/student/QuestionBanksPage';
import DigitalResourcesPage from './pages/student/DigitalResourcesPage';
import PDFReaderPage from './pages/student/PDFReaderPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/librarian/login" element={<StaffLoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Student & Librarian authenticated routes */}
          <Route path="/" element={
            <ProtectedRoute allowedRoles={['student']}>
              <StudentLayout />
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="books" element={<BrowseBooksPage />} />
            <Route path="books/:id" element={<BookDetailsPage />} />
            <Route path="reviews" element={<Navigate to="/books?view=reviews" replace />} />
            <Route path="my-books" element={<MyBooksPage />} />
            
            {/* Digital Learning & Academic Resources */}
            <Route path="resources" element={<DigitalResourcesPage />} />
            <Route path="reader/:id" element={<PDFReaderPage />} />
            <Route path="study-together" element={<StudyTogetherPage />} />
            <Route path="study-together/:id" element={<StudyTogetherPage />} />
            <Route path="achievements" element={<AchievementsPage />} />
            <Route path="notes" element={<NotesPage />} />
            <Route path="question-banks" element={<QuestionBanksPage />} />

            <Route path="ai" element={<AIAssistantPage />} />
            <Route path="contributions" element={<Navigate to="/notes?view=submissions" replace />} />
            <Route path="curriculum" element={<StudentCurriculumPage />} />
            <Route path="learning-path" element={<LearningPathPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="quizzes" element={<QuizzesPage />} />
            <Route path="leaderboard" element={<LeaderboardPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="scan" element={<ScanPage />} />

          </Route>
          <Route path="/admin" element={<ProtectedRoute allowedRoles={['librarian','admin']}><StaffLayout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="dashboard" element={<LibrarianDashboardPage />} />
            <Route path="books" element={<BookManagementPage />} />
            <Route path="profile" element={<StaffProfilePage />} />
            <Route path="reader/:id" element={<PDFReaderPage />} />
            <Route path="circulation" element={<CirculationPage />} />
            <Route path="resources" element={<DigitalResourceManagementPage />} />
            <Route path="contributions" element={<ContributionsPage />} />
            <Route path="curricula" element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="quizzes" element={<QuizManagementPage />} />
            <Route path="announcements" element={<AnnouncementsPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="qr" element={<QRManagementPage />} />
            <Route path="qr/scan" element={<ScanPage />} />
            <Route path="users" element={<Navigate to="/admin/student-data" replace />} />
            <Route path="student-data" element={<StudentDataPage />} />
            <Route path="study-moderation" element={<StudyModerationPage />} />
            <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
