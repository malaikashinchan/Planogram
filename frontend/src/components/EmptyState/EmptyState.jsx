import React from 'react';
import styles from './EmptyState.module.css';
import { PackageOpen } from 'lucide-react';

const EmptyState = ({ message = "No data available", icon: Icon = PackageOpen }) => {
  return (
    <div className={styles.emptyState}>
      <Icon size={48} className={styles.icon} />
      <p>{message}</p>
    </div>
  );
};

export default EmptyState;
