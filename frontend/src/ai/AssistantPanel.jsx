import React, { useContext, useState, useRef, useEffect } from 'react';
import { AssistantContext } from '../context/AssistantContext';
import { AuthContext } from '../context/AuthContext';
import { X, Sparkles, Send } from 'lucide-react';
import { aiService } from './aiService';

import { useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import Draggable from 'react-draggable';

const AssistantPanel = () => {
  const { isOpen, toggleAssistant, messages, addMessage, pageContext, currentRole } = useContext(AssistantContext);
  const { user, isAuthenticated } = useContext(AuthContext);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const nodeRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Listen for custom trigger events
  useEffect(() => {
    const handleTrigger = async (e) => {
      const messageContent = e.detail;
      if (!isOpen) {
        toggleAssistant();
      }
      
      const userMessage = { id: Date.now().toString(), role: 'user', content: messageContent };
      addMessage(userMessage);
      setIsLoading(true);
      
      try {
        const response = await aiService.chat({
          message: userMessage.content,
          history: messages.filter(m => m.id !== 'welcome'),
          context: {
            page: pageContext?.page,
            route: pageContext?.route,
            audit_id: pageContext?.audit_id,
            store_id: pageContext?.store_id,
            planogram_id: pageContext?.planogram_id,
            review_id: pageContext?.review_id
          }
        });
        
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: response.message
        });

        if (response.navigate) {
          navigate(response.navigate);
        }
      } catch (error) {
        console.error("AI Chat Error:", error);
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: "Sorry, I am having trouble connecting to my brain right now. Please try again later."
        });
      } finally {
        setIsLoading(false);
      }
    };

    window.addEventListener('trigger-assistant-explanation', handleTrigger);
    return () => window.removeEventListener('trigger-assistant-explanation', handleTrigger);
  }, [isOpen, toggleAssistant, messages, addMessage, pageContext, user, navigate]);

  const isAuthPage = ['/login', '/register', '/verify-email', '/forgot-password', '/reset-password'].includes(location.pathname);

  if (isAuthPage || !isOpen) return null;

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { id: Date.now().toString(), role: 'user', content: input.trim() };
    addMessage(userMessage);
    setInput('');
    setIsLoading(true);

    try {
      // For G1-G3, we are simply passing the message, page context, and history to the backend
      const response = await aiService.chat({
        message: userMessage.content,
        history: messages.filter(m => m.id !== 'welcome'),
        context: {
          page: pageContext?.page,
          route: pageContext?.route,
          audit_id: pageContext?.audit_id,
          store_id: pageContext?.store_id,
          planogram_id: pageContext?.planogram_id,
          review_id: pageContext?.review_id
        }
      });
      
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: response.message
      });

      if (response.navigate) {
        navigate(response.navigate);
      }
    } catch (error) {
      console.error("AI Chat Error:", error);
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: "Sorry, I am having trouble connecting to my brain right now. Please try again later."
      });
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <Draggable handle=".assistant-header" nodeRef={nodeRef}>
    <div ref={nodeRef} style={{
      position: 'fixed',
      bottom: '24px',
      right: '24px',
      width: '380px',
      height: '600px',
      maxHeight: 'calc(100vh - 48px)',
      backgroundColor: 'white',
      borderRadius: '16px',
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 10000,
      overflow: 'hidden',
      border: '1px solid #E5E7EB'
    }}>
      {/* Header */}
      <div className="assistant-header" style={{
        padding: '16px',
        backgroundColor: '#4F46E5',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        cursor: 'move'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles style={{ width: '20px', height: '20px' }} />
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Retail Assistant</h3>
        </div>
        <button 
          onClick={toggleAssistant}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            padding: '4px'
          }}
        >
          <X style={{ width: '20px', height: '20px' }} />
        </button>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        backgroundColor: '#F9FAFB'
      }}>
        {messages.map((msg) => (
          <div key={msg.id} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              maxWidth: '80%',
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: msg.role === 'user' ? '#4F46E5' : 'white',
              color: msg.role === 'user' ? 'white' : '#111827',
              boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
              border: msg.role === 'assistant' ? '1px solid #E5E7EB' : 'none',
              fontSize: '14px',
              lineHeight: '1.5',
              whiteSpace: msg.role === 'user' ? 'pre-wrap' : 'normal'
            }}>
              {msg.role === 'user' ? msg.content : <ReactMarkdown>{msg.content}</ReactMarkdown>}
            </div>
          </div>
        ))}
        {isLoading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: 'white',
              border: '1px solid #E5E7EB',
              fontSize: '14px',
              display: 'flex',
              gap: '4px',
              alignItems: 'center'
            }}>
              <div className="typing-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#9CA3AF' }}></div>
              <div className="typing-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#9CA3AF' }}></div>
              <div className="typing-dot" style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#9CA3AF' }}></div>
              <span style={{ marginLeft: '8px', color: '#6B7280' }}>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '16px', backgroundColor: 'white', borderTop: '1px solid #E5E7EB' }}>
        <form onSubmit={handleSend} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            disabled={isLoading}
            style={{
              flex: 1,
              padding: '10px 16px',
              borderRadius: '9999px',
              border: '1px solid #D1D5DB',
              outline: 'none',
              fontSize: '14px'
            }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            style={{
              backgroundColor: input.trim() && !isLoading ? '#4F46E5' : '#D1D5DB',
              color: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: input.trim() && !isLoading ? 'pointer' : 'not-allowed',
              transition: 'background-color 0.2s'
            }}
          >
            <Send style={{ width: '18px', height: '18px', marginLeft: '2px' }} />
          </button>
        </form>
      </div>
    </div>
    </Draggable>
  );
};

export default AssistantPanel;
