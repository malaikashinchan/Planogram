import React, { useContext } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider, ThemeContext } from './context/ThemeContext';
import { AssistantProvider } from './context/AssistantContext';
import { AppRoutes } from './routes/AppRoutes';
import AssistantButton from './ai/AssistantButton';
import AssistantPanel from './ai/AssistantPanel';
import './index.css';

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <AssistantProvider>
            <AppRoutes />
            <AssistantButton />
            <AssistantPanel />
          </AssistantProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
