import React, { createContext, useState, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { AuthContext } from './AuthContext';

export const AssistantContext = createContext();

const getPageContext = (path) => {
  let page = "unknown";
  let audit_id = null;
  let store_id = null;
  let planogram_id = null;
  let review_id = null;

  if (path.startsWith('/manager/planograms/')) {
    page = "planogram_detail";
    planogram_id = path.split('/').pop();

  } else if (path === '/manager/planograms') {
    page = "planograms";

  } else if (path.startsWith('/manager/stores/')) {
    page = "store_detail";
    store_id = path.split('/').pop();

  } else if (path === '/manager/stores') {
    page = "stores";

  } else if (path.startsWith('/manager/audits/')) {
    page = "audit_detail";
    audit_id = path.split('/').pop();

  } else if (path === '/manager/audits') {
    page = "audits";

  } else if (path === '/manager/products') {
    page = "products";

  } else if (path === '/manager/reviews') {
    page = "reviews";

  } else if (path === '/manager/employees') {
    page = "employees";

  } else if (path === '/manager') {
    page = "dashboard";

  } else if (path.match(/^\/employee\/audit\/[0-9a-f-]+$/)) {
    page = "audit_result";
    audit_id = path.split('/').pop();

  } else if (path === '/employee/audit/new') {
    page = "upload_audit";

  } else if (path === '/employee') {
    page = "employee_home";
  }

  return {
    route: path,
    page,
    audit_id,
    store_id,
    planogram_id,
    review_id
  };
};

export const AssistantProvider = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);

  const [messages, setMessages] = useState([]);

  const { user } = useContext(AuthContext);
  const currentRole = user?.roles?.map(r => r.name).join(',') || null;

  // Reset conversation when role changes
  useEffect(() => {
    setMessages([
      {
        id: `welcome-${currentRole || 'guest'}`,
        role: 'assistant',
        content: "Hi! I'm your Retail Assistant.\n\nWhat can I help you with?",
      }
    ]);
  }, [currentRole]);

  const location = useLocation();

  // Always derive page context directly from the current route.
  const pageContext = getPageContext(location.pathname);

  const toggleAssistant = () => {
    setIsOpen(prev => !prev);
  };

  const addMessage = (msg) => {
    setMessages(prev => [...prev, msg]);
  };

  return (
    <AssistantContext.Provider
      value={{
        isOpen,
        toggleAssistant,
        messages,
        addMessage,
        pageContext,
        currentRole
      }}
    >
      {children}
    </AssistantContext.Provider>
  );
};