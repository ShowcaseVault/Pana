import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Recordings from './pages/Recordings';
import DashboardLayout from './layouts/DashboardLayout';
import './App.css';

// Placeholder pages for now
const Journals = () => <div style={{padding: '2rem'}}><h2>Journals</h2><p>Coming soon...</p></div>;
const History = () => <div style={{padding: '2rem'}}><h2>History</h2><p>Coming soon...</p></div>;
const Settings = () => <div style={{padding: '2rem'}}><h2>Preferences</h2><p>Coming soon...</p></div>;

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" />;
  
  return children;
};

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route path="/" element={
        <ProtectedRoute>
          <DashboardLayout />
        </ProtectedRoute>
      }>
         <Route index element={<Navigate to="/home" replace />} />
         <Route path="home" element={<Dashboard />} />
         <Route path="recordings" element={<Recordings />} />
         <Route path="journals" element={<Journals />} />
         <Route path="history" element={<History />} />
         <Route path="preferences" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;
