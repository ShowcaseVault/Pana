import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/useAuth';
import Login from './pages/Login';
import Home from './pages/Home';
import Recordings from './pages/Recordings';
import DashboardLayout from './layouts/DashboardLayout';
import Diary from './pages/Diary';
import Calendar from './pages/Calendar';
import './App.css';

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
         <Route path="home" element={<Home />} />
         <Route path="recordings" element={<Recordings />} />
         <Route path="diary" element={<Diary />} />
         <Route path="calendar/:year?/:month?" element={<Calendar />} />
         <Route path="preferences" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;
