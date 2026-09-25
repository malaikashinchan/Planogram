import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import auditService from '../../services/auditService';
import Button from '../../components/Button/Button';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import EmptyState from '../../components/EmptyState/EmptyState';
import { Camera } from 'lucide-react';
import styles from './EmployeeHome.module.css';

const EmployeeHome = () => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAudits = async () => {
      try {
        // Fetch recent audits. Limit increased to 100 to support pagination.
        const data = await auditService.getAudits(0, 100);
        setAudits(data);
      } catch (err) {
        setError('Failed to load recent audits.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAudits();
  }, []);

  const totalPages = Math.ceil(audits.length / itemsPerPage);
  const currentAudits = audits.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const getStatusBadge = (status) => {
    switch(status) {
      case 'PENDING': return <Badge variant="warning">Pending</Badge>;
      case 'PROCESSING': return <Badge variant="info">Processing</Badge>;
      case 'REVIEW_REQUIRED': return <Badge variant="warning">Needs Review</Badge>;
      case 'COMPLETED': return <Badge variant="success">Completed</Badge>;
      case 'FAILED': return <Badge variant="danger">Failed</Badge>;
      default: return <Badge>{status}</Badge>;
    }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className={styles.container}>
      <div className={styles.hero}>
        <Camera size={48} className={styles.heroIcon} />
        <h2>Shelf Audit</h2>
        <p>Capture shelf conditions to analyze compliance</p>
        <Button 
          size="large" 
          onClick={() => navigate('/employee/audit/new')}
          style={{ width: '100%', maxWidth: '300px' }}
        >
          Start New Audit
        </Button>
      </div>

      <div className={styles.section}>
        <h3>Recent Audits</h3>
        {audits.length === 0 ? (
          <EmptyState message="You haven't submitted any audits yet." />
        ) : (
          <>
            <div className={styles.auditList}>
              {currentAudits.map(audit => (
                <Link to={`/employee/audit/${audit.id}`} key={audit.id} className={styles.auditCard}>
                  <div className={styles.auditInfo}>
                    <span className={styles.storeName}>{audit.store?.name || 'Unknown Store'}</span>
                    <span className={styles.dateText}>{audit.planogram?.name || 'Unknown Planogram'}</span>
                    <span className={styles.dateText}>{new Date(audit.created_at).toLocaleString()}</span>
                  </div>
                  <div className={styles.auditStatus}>
                    {getStatusBadge(audit.status)}
                  </div>
                </Link>
              ))}
            </div>
            
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '2rem', gap: '0.5rem', alignItems: 'center' }}>
                <Button 
                  variant="outline" 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  style={{ padding: '0.5rem 1rem', background: 'white', border: '1px solid #e0e0e0', color: '#333' }}
                >
                  &lt; Back
                </Button>
                
                {[...Array(totalPages)].map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentPage(i + 1)}
                    style={{
                      padding: '0.5rem 1rem',
                      background: currentPage === i + 1 ? '#000' : 'white',
                      color: currentPage === i + 1 ? 'white' : '#333',
                      border: '1px solid #e0e0e0',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontWeight: currentPage === i + 1 ? 'bold' : 'normal'
                    }}
                  >
                    {i + 1}
                  </button>
                ))}
                
                <Button 
                  variant="outline"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  style={{ padding: '0.5rem 1rem', background: 'white', border: '1px solid #e0e0e0', color: '#333' }}
                >
                  Next &gt;
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default EmployeeHome;
