import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../../services/authService';
import Input from '../../components/Input/Input';
import Button from '../../components/Button/Button';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import styles from './Auth.module.css';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const data = await authService.forgotPassword(email);
      setSuccess(data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send reset link.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h2 className={styles.title}>Reset Password</h2>
        <ErrorMessage message={error} />
        {success ? (
          <div style={{ color: 'green', marginBottom: '1rem', textAlign: 'center' }}>
            {success}
            <br /><br />
            <Link to="/login">Return to Login</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: '#666' }}>
              Enter your email address and we'll send you a link to reset your password.
            </p>
            <div className={styles.formGroup}>
              <label className={styles.label}>Email</label>
              <Input 
                type="email" 
                value={email} 
                onChange={e => setEmail(e.target.value)} 
                required 
              />
            </div>
            <Button type="submit" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Sending...' : 'Send Reset Link'}
            </Button>
          </form>
        )}
        <div className={styles.footer}>
          Remember your password? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
