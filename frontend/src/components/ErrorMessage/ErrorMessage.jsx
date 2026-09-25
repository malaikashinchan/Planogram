import React from 'react';
import styles from './ErrorMessage.module.css';

const ErrorMessage = ({ message }) => {
  if (!message) return null;
  
  // Handle FastAPI 422 Validation Error arrays or other objects
  const displayMessage = typeof message === 'string' 
    ? message 
    : (Array.isArray(message) ? message.map(m => m.msg || JSON.stringify(m)).join(', ') : JSON.stringify(message));
  
  return (
    <div className={styles.error}>
      {displayMessage}
    </div>
  );
};

export default ErrorMessage;
