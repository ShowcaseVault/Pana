import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import '../styles/shell.css';

const DashboardLayout = () => (
  <div className="shell">
    <Sidebar />
    <main className="shell__main">
      <Outlet />
    </main>
  </div>
);

export default DashboardLayout;
