import React, { useContext } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider, ThemeContext } from './context/ThemeContext';
import { AppRoutes } from './routes/AppRoutes';
import './index.css';

const GlobalThemeToggle = () => {
  const { isDarkMode, toggleTheme } = useContext(ThemeContext);
  return (
    <button 
      onClick={toggleTheme} 
      style={{
        position: 'fixed',
        bottom: '1rem',
        right: '1rem',
        background: 'var(--surface-color)',
        color: 'var(--text-color)',
        border: '1px solid var(--border-color)',
        padding: '0.5rem',
        borderRadius: '50%',
        width: '40px',
        height: '40px',
        cursor: 'pointer',
        boxShadow: 'var(--card-shadow)',
        zIndex: 1000
      }}
      title="Toggle Theme"
    >
      {isDarkMode ? '☀️' : '🌙'}
    </button>
  );
};

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <GlobalThemeToggle />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
