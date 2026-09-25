import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import authService from '../../services/authService';
import Input from '../../components/Input/Input';
import Button from '../../components/Button/Button';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import styles from './Auth.module.css';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    organization_name: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleChange = (e) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const data = await authService.register(formData);
      setSuccess(data.message);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h2 className={styles.title}>Create an Account</h2>
        <ErrorMessage message={error} />
        {success ? (
          <div style={{ color: 'green', marginBottom: '1rem', textAlign: 'center' }}>
            {success}
            <br /><br />
            <Link to="/login">Go to Login</Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <label className={styles.label}>Organization Name</label>
              <Input type="text" name="organization_name" value={formData.organization_name} onChange={handleChange} required />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>First Name</label>
              <Input type="text" name="first_name" value={formData.first_name} onChange={handleChange} required />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>Last Name</label>
              <Input type="text" name="last_name" value={formData.last_name} onChange={handleChange} required />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>Email</label>
              <Input type="email" name="email" value={formData.email} onChange={handleChange} required />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.label}>Password</label>
              <Input type="password" name="password" value={formData.password} onChange={handleChange} required />
            </div>
            <Button type="submit" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Registering...' : 'Register'}
            </Button>
          </form>
        )}
        <div className={styles.footer}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
