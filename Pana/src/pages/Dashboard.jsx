import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard-container" style={{ padding: '20px' }}>
      <h1>Dashboard</h1>
      {user ? (
        <div className="profile-card">
          <img 
            src={user.picture} 
            alt={user.name} 
            style={{ borderRadius: '50%', width: '100px', height: '100px' }}
          />
          <h2>Hello, {user.name}!</h2>
          <p>Email: {user.email}</p>
          <button onClick={logout} style={{ marginTop: '20px', padding: '8px 16px' }}>
            Logout
          </button>
        </div>
      ) : (
        <p>Loading user data...</p>
      )}
    </div>
  );
};

export default Dashboard;
