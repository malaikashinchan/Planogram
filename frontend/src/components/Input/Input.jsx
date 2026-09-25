import React, { useState } from 'react';
import { Eye, EyeOff, Check, X } from 'lucide-react';
import styles from './Input.module.css';

const Input = ({ type = 'text', ...props }) => {
  const [showPassword, setShowPassword] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [showErrorMsg, setShowErrorMsg] = useState(false);
  
  const isPassword = type === 'password';
  const val = props.value || '';

  const requirements = [
    { label: 'At least 8 characters', met: val.length >= 8 },
    { label: 'At least 1 uppercase letter', met: /[A-Z]/.test(val) },
    { label: 'At least 1 number', met: /[0-9]/.test(val) }
  ];

  const allMet = requirements.every(r => r.met);

  const handleFocus = (e) => {
    setIsFocused(true);
    if (props.onFocus) props.onFocus(e);
  };

  const handleBlur = (e) => {
    setIsFocused(false);
    if (props.onBlur) props.onBlur(e);
  };

  const handleInvalid = (e) => {
    if (isPassword && !allMet) {
      e.preventDefault();
      setShowErrorMsg(true);
    }
    if (props.onInvalid) props.onInvalid(e);
  };
  
  const handleChange = (e) => {
    if (showErrorMsg && allMet) setShowErrorMsg(false);
    if (props.onChange) props.onChange(e);
  };

  const dynamicProps = { ...props };
  if (isPassword) {
    // If rules are not met, use an impossible pattern so HTML5 validation fails.
    dynamicProps.pattern = allMet ? ".*" : "(?=a)b";
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.container}>
        <input 
          className={styles.input} 
          type={isPassword && showPassword ? 'text' : type} 
          onFocus={handleFocus}
          onBlur={handleBlur}
          onInvalid={handleInvalid}
          onChange={handleChange}
          {...dynamicProps} 
        />
        {isPassword && (
          <button
            type="button"
            className={styles.toggleBtn}
            onClick={() => setShowPassword(!showPassword)}
            title={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <Eye size={20} /> : <EyeOff size={20} />}
          </button>
        )}
      </div>

      {isPassword && isFocused && (
        <div className={styles.checklist}>
          {requirements.map((req, idx) => (
            <div key={idx} className={styles.checklistItem}>
              {req.met ? <Check size={14} color="green" /> : <X size={14} color="red" />}
              <span style={{ color: req.met ? 'green' : 'red', marginLeft: '6px' }}>{req.label}</span>
            </div>
          ))}
        </div>
      )}

      {isPassword && showErrorMsg && !allMet && (
        <div className={styles.errorMsg}>
          enter correct password
        </div>
      )}
    </div>
  );
};

export default Input;

