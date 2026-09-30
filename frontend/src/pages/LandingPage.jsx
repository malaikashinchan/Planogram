import React, { useContext } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import { ScanLine, BarChart3, Clock, Zap, Sun, Moon } from 'lucide-react';
import styles from './LandingPage.module.css';

const LandingPage = () => {
  const { user, isAuthenticated } = useContext(AuthContext);
  const { isDarkMode, toggleTheme } = useContext(ThemeContext);

  // Only redirect if we are TRULY authenticated with a valid user object and roles
  if (isAuthenticated && user && Array.isArray(user.roles) && user.roles.length > 0) {
    const roles = user.roles;
    if (roles.includes('ADMIN') || roles.includes('MANAGER')) {
      return <Navigate to="/manager" replace />;
    }
    if (roles.includes('EMPLOYEE')) {
      return <Navigate to="/employee" replace />;
    }
  }

  return (
    <div className={styles.landingPage}>
      {/* HEADER */}
      <header className={styles.header}>
        <Link to="/" className={styles.logo}>
          <ScanLine size={28} />
          Planogram AI
        </Link>
        <div className={styles.navLinks}>
          <a href="#features" className={styles.navLink}>Features</a>
          <Link to="/login" className={styles.navLink} style={{ fontWeight: 'bold', marginRight: '1rem' }}>Sign In</Link>
          <button 
            onClick={toggleTheme} 
            style={{ display: 'flex', alignItems: 'center', background: 'transparent', border: 'none', color: 'var(--text-color)', cursor: 'pointer', fontSize: '1rem', padding: '0' }}
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
      </header>

      {/* HERO SECTION */}
      <section className={styles.hero}>
        <div className={styles.heroContent}>
          <div className={styles.heroTag}>Planogram optimization software</div>
          <h1 className={styles.heroTitle}>Optimize your store's planograms to avoid stockouts and lost sales</h1>
          <p className={styles.heroSubtitle}>
            Accurate planogram software helps avoid stockouts and lost sales while reducing excess stock and decreasing waste. A unified approach with a shared data source improves collaboration between supply chain and store operations, increasing accuracy and improving efficiency.
          </p>
          <div className={styles.heroButtons}>
            <Link to="/login" className={styles.btnPrimary}>Sign In to App</Link>
          </div>
        </div>
        <div className={styles.heroImage}>
          {/* A simple placeholder box for the image taking inspiration from RELEX */}
          <div style={{ width: '500px', height: '400px', background: 'linear-gradient(45deg, var(--primary-color), var(--primary-hover))', borderRadius: '30px 100px 30px 30px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ background: 'var(--surface-color)', padding: '2rem', borderRadius: '12px', width: '80%', color: 'var(--text-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1rem' }}>
                <span style={{ fontWeight: 'bold' }}>Planograms</span>
                <span style={{ color: 'var(--success-color)' }}>100% Compliance</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ height: '20px', background: 'var(--bg-color-alt)', borderRadius: '4px', width: '100%' }}></div>
                <div style={{ height: '20px', background: 'var(--bg-color-alt)', borderRadius: '4px', width: '80%' }}></div>
                <div style={{ height: '20px', background: 'var(--bg-color-alt)', borderRadius: '4px', width: '90%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section id="features" className={styles.features}>
        <h2 className={styles.featuresTitle}>Set your stores apart with AI</h2>
        <div className={styles.featureGrid}>
          <div className={styles.featureCard}>
            <BarChart3 size={32} className={styles.featureIcon} />
            <h3>Create store-specific planograms at scale</h3>
            <p>See up to 5+% availability and up to 3+% sales by automating the production of locally optimized planograms powered by Deep Learning.</p>
          </div>
          <div className={styles.featureCard}>
            <Zap size={32} className={styles.featureIcon} />
            <h3>Collaborate with stores</h3>
            <p>Empower your on-ground employees to instantly capture shelf conditions using our streamlined mobile interface and real-time YOLO computer vision.</p>
          </div>
          <div className={styles.featureCard}>
            <Clock size={32} className={styles.featureIcon} />
            <h3>Sync store space and replenishment</h3>
            <p>Reduce cost-to-serve and drive better profitability. Leverage AI-driven demand forecasting to keep your store space in sync with changing customer demand.</p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className={styles.footer}>
        <div className={styles.footerGrid}>
          <div className={styles.footerColumn}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem', fontWeight: 'bold', color: 'white', marginBottom: '1.5rem' }}>
              <ScanLine size={24} color="white" /> Planogram AI
            </div>
            <p style={{ color: '#94a3b8', lineHeight: '1.6' }}>
              The unified platform for retail planning and supply chain execution.
            </p>
          </div>
          <div className={styles.footerColumn}>
            <h4>Company</h4>
            <ul>
              <li><a href="#">About us</a></li>
              <li><a href="#">Careers</a></li>
              <li><a href="#">Customers</a></li>
              <li><a href="#">Events</a></li>
            </ul>
          </div>
          <div className={styles.footerColumn}>
            <h4>Helpful Guides</h4>
            <ul>
              <li><a href="#">Build a better DIY supply chain</a></li>
              <li><a href="#">Category management</a></li>
              <li><a href="#">Demand forecasting for retail</a></li>
            </ul>
          </div>
          <div className={styles.footerColumn}>
            <h4>Security</h4>
            <ul>
              <li><a href="#">Privacy Trust Center</a></li>
              <li><a href="#">Information Security FAQ</a></li>
              <li><a href="#">AI Governance & Trust</a></li>
            </ul>
          </div>
        </div>
        <div className={styles.footerBottom}>
          <div>&copy; 2026 Planogram AI Inc. All rights reserved.</div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <a href="#" style={{ color: '#94a3b8', textDecoration: 'none' }}>Terms of Service</a>
            <a href="#" style={{ color: '#94a3b8', textDecoration: 'none' }}>Privacy Policy</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
