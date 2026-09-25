import React from 'react';
import styles from './Badge.module.css';

const Badge = ({ children, variant = 'info' }) => {
  return (
    <span className={`${styles.badge} ${styles[variant]}`}>
      {children}
    </span>
  );
};

export default Badge;
