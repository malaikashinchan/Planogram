import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import storeService from '../../services/storeService';
import planogramService from '../../services/planogramService';
import auditService from '../../services/auditService';
import Button from '../../components/Button/Button';
import Select from '../../components/Select/Select';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import { Store, LayoutTemplate, Camera, Upload, CheckCircle, Loader2 } from 'lucide-react';
import styles from './AuditWizard.module.css';

const AuditWizard = () => {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();

  // Data
  const [stores, setStores] = useState([]);
  const [planograms, setPlanograms] = useState([]);
  
  // Selection state
  const [selectedStore, setSelectedStore] = useState('');
  const [selectedPlanogram, setSelectedPlanogram] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  
  // Async state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [pollingAuditId, setPollingAuditId] = useState(null);
  const [auditStatus, setAuditStatus] = useState(null);

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const storeData = await storeService.getStores();
        setStores(storeData);
      } catch (err) {
        setError('Failed to load stores.');
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  useEffect(() => {
    const fetchPlanograms = async () => {
      if (!selectedStore) return;
      try {
        const planoData = await planogramService.getPlanograms(selectedStore);
        setPlanograms(planoData);
      } catch (err) {
        setError('Failed to load planograms for this store.');
      }
    };
    fetchPlanograms();
  }, [selectedStore]);

  // Polling logic
  useEffect(() => {
    let intervalId;
    if (pollingAuditId) {
      const poll = async () => {
        try {
          const audit = await auditService.getAudit(pollingAuditId);
          setAuditStatus(audit.status);
          
          if (audit.status === 'COMPLETED' || audit.status === 'FAILED' || audit.status === 'PENDING_REVIEW') {
            clearInterval(intervalId);
            // After 1.5 seconds, redirect to the result page
            setTimeout(() => {
              navigate(`/employee/audit/${pollingAuditId}`);
            }, 1500);
          }
        } catch (err) {
          console.error('Polling error', err);
        }
      };
      
      intervalId = setInterval(poll, 3000); // Poll every 3 seconds
      poll(); // Immediate first call
    }
    
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [pollingAuditId, navigate]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    if (!selectedStore || !selectedPlanogram || !imageFile) return;
    
    setSubmitting(true);
    setError('');
    
    try {
      const audit = await auditService.createAudit(selectedStore, selectedPlanogram, imageFile);
      setPollingAuditId(audit.id);
      setStep(4);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit audit.');
      setSubmitting(false);
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className={styles.wizardContainer}>
      <div className={styles.progressHeader}>
        <div className={`${styles.stepIndicator} ${step >= 1 ? styles.active : ''}`}>1. Store</div>
        <div className={styles.stepLine}></div>
        <div className={`${styles.stepIndicator} ${step >= 2 ? styles.active : ''}`}>2. Planogram</div>
        <div className={styles.stepLine}></div>
        <div className={`${styles.stepIndicator} ${step >= 3 ? styles.active : ''}`}>3. Capture</div>
        <div className={styles.stepLine}></div>
        <div className={`${styles.stepIndicator} ${step >= 4 ? styles.active : ''}`}>4. Process</div>
      </div>

      <div className={styles.wizardCard}>
        <ErrorMessage message={error} />

        {step === 1 && (
          <div className={styles.stepContent}>
            <h3><Store size={20} className={styles.icon} /> Select Store</h3>
            <Select 
              value={selectedStore} 
              onChange={e => setSelectedStore(e.target.value)}
            >
              <option value="">-- Choose a Store --</option>
              {stores.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
            <div className={styles.stepFooter}>
              <Button onClick={() => navigate('/employee')} variant="secondary">Cancel</Button>
              <Button onClick={() => setStep(2)} disabled={!selectedStore}>Continue</Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className={styles.stepContent}>
            <h3><LayoutTemplate size={20} className={styles.icon} /> Select Planogram</h3>
            {planograms.length === 0 ? (
              <div style={{ color: 'var(--text-light)', marginBottom: '1rem' }}>No active planograms found for this store.</div>
            ) : (
              <Select 
                value={selectedPlanogram} 
                onChange={e => setSelectedPlanogram(e.target.value)}
              >
                <option value="">-- Choose a Planogram --</option>
                {planograms.map(p => (
                  <option key={p.id} value={p.id}>{p.name} (v{p.version || 1})</option>
                ))}
              </Select>
            )}
            <div className={styles.stepFooter}>
              <Button onClick={() => setStep(1)} variant="secondary">Back</Button>
              <Button onClick={() => setStep(3)} disabled={!selectedPlanogram}>Continue</Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className={styles.stepContent}>
            <h3><Camera size={20} className={styles.icon} /> Capture Shelf Image</h3>
            
            <div className={styles.imageUploader}>
              {imagePreview ? (
                <div className={styles.previewContainer}>
                  <img src={imagePreview} alt="Shelf preview" className={styles.previewImage} />
                  <label className={styles.changeImageBtn}>
                    Change Image
                    <input type="file" accept="image/*" onChange={handleImageChange} hidden />
                  </label>
                </div>
              ) : (
                <label className={styles.uploadPrompt}>
                  <Upload size={32} />
                  <span>Tap to upload or take photo</span>
                  <input type="file" accept="image/*" onChange={handleImageChange} hidden />
                </label>
              )}
            </div>

            <div className={styles.stepFooter}>
              <Button onClick={() => setStep(2)} variant="secondary" disabled={submitting}>Back</Button>
              <Button onClick={handleSubmit} disabled={!imageFile || submitting}>
                {submitting ? 'Uploading...' : 'Submit Audit'}
              </Button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className={styles.processingContent}>
            <div className={styles.processingSpinner}>
              {auditStatus === 'COMPLETED' || auditStatus === 'PENDING_REVIEW' ? (
                <CheckCircle size={64} color="var(--success-color)" />
              ) : auditStatus === 'FAILED' ? (
                <div style={{ color: 'var(--danger-color)' }}>X</div>
              ) : (
                <Loader2 size={64} className={styles.spinningIcon} color="var(--primary-color)" />
              )}
            </div>
            <h3>
              {auditStatus === 'COMPLETED' ? 'Analysis Complete!' :
               auditStatus === 'PENDING_REVIEW' ? 'Analysis Complete (Needs Review)' :
               auditStatus === 'FAILED' ? 'Analysis Failed' :
               'Analyzing Image...'}
            </h3>
            
            <div className={styles.statusSteps}>
              <div className={styles.statusStep}>
                <span>Uploading Image</span>
                <span className={styles.statusDone}>✓</span>
              </div>
              <div className={styles.statusStep}>
                <span>Detecting Products</span>
                {auditStatus === 'PENDING' ? <span className={styles.statusPending}>...</span> : <span className={styles.statusDone}>✓</span>}
              </div>
              <div className={styles.statusStep}>
                <span>Checking Planogram</span>
                {auditStatus === 'PROCESSING' || auditStatus === 'PENDING' ? <span className={styles.statusPending}>...</span> : <span className={styles.statusDone}>✓</span>}
              </div>
              <div className={styles.statusStep}>
                <span>Generating Results</span>
                {auditStatus === 'COMPLETED' || auditStatus === 'PENDING_REVIEW' ? <span className={styles.statusDone}>✓</span> : <span className={styles.statusPending}>...</span>}
              </div>
            </div>
            
            <p className={styles.processingNote}>
              {auditStatus === 'COMPLETED' || auditStatus === 'PENDING_REVIEW' ? 'Redirecting to results...' : 'This usually takes 10-30 seconds.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditWizard;
