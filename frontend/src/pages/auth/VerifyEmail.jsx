import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import authService from '../../services/authService';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import styles from './Auth.module.css';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('No verification token provided.');
        return;
      }

      try {
        const data = await authService.verifyEmail(token);
        setStatus('success');
        setMessage(data.message);
      } catch (err) {
        setStatus('error');
        setMessage(err.response?.data?.detail || 'Verification failed. The token may be invalid or expired.');
      }
    };

    verify();
  }, [token]);

  return (
    <div className={styles.container}>
      <div className={styles.card} style={{ textAlign: 'center' }}>
        <h2 className={styles.title}>Email Verification</h2>
        
        {status === 'verifying' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Spinner />
            <p style={{ marginTop: '1rem' }}>Verifying your email...</p>
          </div>
        )}

        {status === 'success' && (
          <div>
            <div style={{ color: 'green', marginBottom: '1rem' }}>{message}</div>
            <Link to="/login">Click here to log in</Link>
          </div>
        )}

        {status === 'error' && (
          <div>
            <ErrorMessage message={message} />
            <Link to="/login">Return to Login</Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default VerifyEmail;
