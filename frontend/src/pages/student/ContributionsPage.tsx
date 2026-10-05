import { Navigate } from 'react-router-dom';
export default function ContributionsPage() {
  return <Navigate to="/notes?view=submissions" replace />;
}
