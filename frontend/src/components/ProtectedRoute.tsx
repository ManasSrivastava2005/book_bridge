import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface Props {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export default function ProtectedRoute({ children, allowedRoles }: Props) {
  const location = useLocation();
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const staffRoute = location.pathname === '/admin' || location.pathname.startsWith('/admin/');
  if (!user) return <Navigate to={staffRoute ? '/librarian/login' : '/login'} state={{from: location.pathname + location.search}} replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to={user.role === 'student' ? '/dashboard' : '/admin/dashboard'} replace />;

  return <>{children}</>;
}
