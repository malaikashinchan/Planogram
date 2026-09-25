import React from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import { LayoutDashboard, Store, Package, LayoutTemplate, ClipboardCheck, Users, BrainCircuit, LogOut } from 'lucide-react';
import styles from './ManagerLayout.module.css';

const ManagerLayout = () => {
  const { user, logout } = useContext(AuthContext);
  const { isDarkMode, toggleTheme } = useContext(ThemeContext);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/manager', icon: LayoutDashboard },
    { name: 'Stores', path: '/manager/stores', icon: Store },
    { name: 'Products', path: '/manager/products', icon: Package },
    { name: 'Planograms', path: '/manager/planograms', icon: LayoutTemplate },
    { name: 'Audits', path: '/manager/audits', icon: ClipboardCheck },
    { name: 'Reviews', path: '/manager/reviews', icon: BrainCircuit },
    { name: 'Staff', path: '/manager/employees', icon: Users },
  ];

  return (
    <div className={styles.layout}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h2>Planogram AI</h2>
        </div>
        <nav className={styles.nav}>
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || (item.path !== '/manager' && location.pathname.startsWith(item.path));
            return (
              <Link 
                key={item.name} 
                to={item.path} 
                className={`${styles.navItem} ${isActive ? styles.active : ''}`}
              >
                <Icon size={20} className={styles.icon} />
                {item.name}
              </Link>
            );
          })}
        </nav>
        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{user?.first_name} {user?.last_name}</span>
            <span className={styles.userRole}>Manager</span>
          </div>
          <button onClick={handleLogout} className={styles.logoutBtn}>
            <LogOut size={20} className={styles.icon} />
            Logout
          </button>
        </div>
      </aside>
      <main className={styles.main}>
        <header className={styles.header}>
          <h1>{navItems.find(item => location.pathname === item.path || (item.path !== '/manager' && location.pathname.startsWith(item.path)))?.name || 'Dashboard'}</h1>
          <button onClick={toggleTheme} className={styles.themeToggleBtn}>
            {isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </header>
        <div className={styles.content}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default ManagerLayout;
