import React, { useContext, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { AssistantContext } from '../context/AssistantContext';
import { AuthContext } from '../context/AuthContext';
import { Sparkles } from 'lucide-react';
import Draggable from 'react-draggable';

const AssistantButton = () => {
  const { toggleAssistant, isOpen } = useContext(AssistantContext);
  const { isAuthenticated } = useContext(AuthContext);
  const location = useLocation();
  const nodeRef = useRef(null);

  const isAuthPage = ['/login', '/register', '/verify-email', '/forgot-password', '/reset-password'].includes(location.pathname);

  if (isAuthPage || isOpen) return null;

  return (
    <Draggable nodeRef={nodeRef}>
      <button
        ref={nodeRef}
        onClick={toggleAssistant}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '12px 20px',
          backgroundColor: '#4F46E5', // Indigo-600
          color: 'white',
          border: 'none',
          borderRadius: '9999px',
          fontWeight: '600',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          cursor: 'move', // Changed from pointer to move
          transition: 'background-color 0.2s', // Removed transform transition to avoid conflict with Draggable
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.backgroundColor = '#4338CA'; // Indigo-700
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.backgroundColor = '#4F46E5';
        }}
      >
        <Sparkles style={{ width: '20px', height: '20px', pointerEvents: 'none' }} />
        <span style={{ pointerEvents: 'none' }}>Ask Assistant</span>
      </button>
    </Draggable>
  );
};

export default AssistantButton;
