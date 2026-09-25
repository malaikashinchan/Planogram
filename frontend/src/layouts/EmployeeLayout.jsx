import React, { useContext } from 'react';
import { Outlet, useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { LogOut, ScanLine } from 'lucide-react';
import styles from './EmployeeLayout.module.css';

const EmployeeLayout = () => {
  const { logout, user } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className={styles.layout}>
      <header className={styles.header}>
        <Link to="/employee" style={{ textDecoration: 'none' }}>
          <h1><ScanLine size={24} /> Planogram AI</h1>
        </Link>
        <div className={styles.headerRight}>
          <span style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>
            {user?.first_name}
          </span>
          <button onClick={handleLogout} className={styles.logoutBtn}>
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
};

export default EmployeeLayout;
