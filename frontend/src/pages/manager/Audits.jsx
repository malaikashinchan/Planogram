import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import auditService from '../../services/auditService';
import Table from '../../components/Table/Table';
import Badge from '../../components/Badge/Badge';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import EmptyState from '../../components/EmptyState/EmptyState';

const Audits = () => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAudits = async () => {
      try {
        const data = await auditService.getAudits();
        setAudits(data);
      } catch (err) {
        setError('Failed to load audits.');
      } finally {
        setLoading(false);
      }
    };
    fetchAudits();
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED': return <Badge variant="success">COMPLETED</Badge>;
      case 'PENDING_REVIEW': return <Badge variant="warning">PENDING REVIEW</Badge>;
      case 'PROCESSING': return <Badge variant="info">PROCESSING</Badge>;
      case 'FAILED': return <Badge variant="danger">FAILED</Badge>;
      default: return <Badge variant="info">{status}</Badge>;
    }
  };

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Audit History</h2>
      </div>

      {audits.length === 0 ? (
        <EmptyState message="No audits have been performed yet." />
      ) : (
        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <Table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Store</th>
                <th>Planogram</th>
                <th>Status</th>
                <th>Compliance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {audits.map(audit => (
                <tr key={audit.id}>
                  <td>{new Date(audit.created_at).toLocaleString()}</td>
                  <td>{audit.store?.name || '-'}</td>
                  <td>{audit.planogram?.name || '-'}</td>
                  <td>{getStatusBadge(audit.status)}</td>
                  <td>
                    {audit.compliance_score !== null 
                      ? `${(audit.compliance_score * 100).toFixed(1)}%` 
                      : '-'}
                  </td>
                  <td>
                    <button 
                      onClick={() => navigate(`/manager/audits/${audit.id}`)}
                      style={{ color: '#007bff', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </div>
  );
};

export default Audits;
