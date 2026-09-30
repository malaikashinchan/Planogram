import React, { useContext } from 'react';
import { Outlet, useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import { LogOut, ScanLine, Sun, Moon } from 'lucide-react';
import styles from './EmployeeLayout.module.css';

const EmployeeLayout = () => {
  const { logout, user } = useContext(AuthContext);
  const { isDarkMode, toggleTheme } = useContext(ThemeContext);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
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
          <button 
            onClick={toggleTheme} 
            className={styles.themeToggleBtn}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-color)', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem' }}
          >
            {isDarkMode ? <><Sun size={16} /> Light Mode</> : <><Moon size={16} /> Dark Mode</>}
          </button>
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
