import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

const DashboardLayout = () => {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>

      <style>{`
        .dashboard-layout {
          display: flex;
          width: 100vw;
          height: 100vh;
          overflow: hidden;
          background-color: var(--bg-primary);
        }

        .main-content {
          flex: 1;
          height: 100%;
          overflow-y: auto;
          position: relative;
        }
      `}</style>
    </div>
  );
};

export default DashboardLayout;
