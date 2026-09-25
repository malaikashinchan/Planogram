import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import auditService from '../../services/auditService';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import Button from '../../components/Button/Button';
import { ChevronLeft, AlertTriangle } from 'lucide-react';

const AuditResult = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [audit, setAudit] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [violations, setViolations] = useState([]);
  const [activeFilter, setActiveFilter] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAuditAndReviews = async () => {
      try {
        const [auditData, reviewsData, violationsData] = await Promise.all([
          auditService.getAudit(id),
          auditService.getAuditReviews(id).catch(() => []), // Optional fetch
          auditService.getAuditViolations(id).catch(() => []) // Optional fetch
        ]);
        setAudit(auditData);
        setReviews(reviewsData);
        setViolations(violationsData);
      } catch (err) {
        setError('Failed to load audit results.');
      } finally {
        setLoading(false);
      }
    };
    fetchAuditAndReviews();
  }, [id]);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!audit) return null;

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <button 
        onClick={() => navigate(-1)} 
        style={{ background: 'none', border: 'none', color: 'var(--primary-color)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', marginBottom: '1.5rem', fontSize: '1rem' }}
      >
        <ChevronLeft size={20} /> Back
      </button>

      <div style={{ background: 'var(--surface-color)', padding: '2rem', borderRadius: '12px', boxShadow: 'var(--card-shadow)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ margin: '0 0 0.5rem 0' }}>Audit Results</h2>
            <div style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>
              {new Date(audit.created_at).toLocaleString()}
            </div>
          </div>
          <Badge variant={
            audit.status === 'COMPLETED' ? 'success' : 
            audit.status === 'REVIEW_REQUIRED' ? 'warning' : 'danger'
          }>
            {audit.status}
          </Badge>
        </div>

        {audit.status === 'FAILED' ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--danger-color)' }}>
            <AlertTriangle size={48} style={{ marginBottom: '1rem' }} />
            <h3>Processing Failed</h3>
            <p style={{ color: 'var(--text-color)' }}>We could not process this image. Please try capturing the shelf again with better lighting and clearer focus.</p>
            <Button onClick={() => navigate('/employee/audit/new')} style={{ marginTop: '1rem' }}>Capture Again</Button>
          </div>
        ) : audit.status === 'NEEDS_RETAKE' ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--warning-color)' }}>
            <AlertTriangle size={48} style={{ marginBottom: '1rem' }} />
            <h3>Needs Retake</h3>
            <p style={{ color: 'var(--text-color)' }}>The AI could not detect any products on the shelf. This is usually due to image blurriness, poor lighting, or being too far away. Please retake the photo.</p>
            <Button onClick={() => navigate('/employee/audit/new')} style={{ marginTop: '1rem' }}>Capture Again</Button>
          </div>
        ) : (
          <>
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
              <div style={{ fontSize: '1.2rem', color: 'var(--text-light)', marginBottom: '0.5rem' }}>Overall Compliance</div>
              <div style={{ fontSize: '4rem', fontWeight: 'bold', color: 'var(--primary-color)' }}>
                {audit.compliance?.availability_rate !== undefined 
                  ? `${(audit.compliance.availability_rate * 100).toFixed(0)}%` 
                  : 'N/A'}
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', marginTop: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>Position Accuracy</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '500' }}>
                    {audit.compliance?.position_accuracy !== undefined 
                      ? `${(audit.compliance.position_accuracy * 100).toFixed(0)}%` 
                      : 'N/A'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-light)' }}>Facing Compliance</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: '500' }}>
                    {audit.compliance?.facing_compliance !== undefined 
                      ? `${(audit.compliance.facing_compliance * 100).toFixed(0)}%` 
                      : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <div 
                onClick={() => setActiveFilter(activeFilter === 'MISSING_PRODUCT' ? null : 'MISSING_PRODUCT')}
                style={{ background: '#fff3cd', padding: '1.5rem', borderRadius: '8px', textAlign: 'center', border: '1px solid #ffeeba', cursor: 'pointer', opacity: activeFilter && activeFilter !== 'MISSING_PRODUCT' ? 0.5 : 1, transition: 'opacity 0.2s' }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#856404' }}>{audit.violations?.missing || 0}</div>
                <div style={{ color: '#856404', fontSize: '0.9rem' }}>Missing</div>
              </div>
              <div 
                onClick={() => setActiveFilter(activeFilter === 'EXTRA_PRODUCT' ? null : 'EXTRA_PRODUCT')}
                style={{ background: '#d4edda', padding: '1.5rem', borderRadius: '8px', textAlign: 'center', border: '1px solid #c3e6cb', cursor: 'pointer', opacity: activeFilter && activeFilter !== 'EXTRA_PRODUCT' ? 0.5 : 1, transition: 'opacity 0.2s' }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#155724' }}>{audit.violations?.extra || 0}</div>
                <div style={{ color: '#155724', fontSize: '0.9rem' }}>Extra</div>
              </div>
              <div 
                onClick={() => setActiveFilter(activeFilter === 'MISPLACED_PRODUCT' ? null : 'MISPLACED_PRODUCT')}
                style={{ background: '#f8d7da', padding: '1.5rem', borderRadius: '8px', textAlign: 'center', border: '1px solid #f5c6cb', cursor: 'pointer', opacity: activeFilter && activeFilter !== 'MISPLACED_PRODUCT' ? 0.5 : 1, transition: 'opacity 0.2s' }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#721c24' }}>{audit.violations?.misplaced || 0}</div>
                <div style={{ color: '#721c24', fontSize: '0.9rem' }}>Misplaced</div>
              </div>
              <div 
                onClick={() => setActiveFilter(activeFilter === 'FACING_MISMATCH' ? null : 'FACING_MISMATCH')}
                style={{ background: '#cce5ff', padding: '1.5rem', borderRadius: '8px', textAlign: 'center', border: '1px solid #b8daff', cursor: 'pointer', opacity: activeFilter && activeFilter !== 'FACING_MISMATCH' ? 0.5 : 1, transition: 'opacity 0.2s' }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#004085' }}>{audit.violations?.facing || 0}</div>
                <div style={{ color: '#004085', fontSize: '0.9rem' }}>Facing</div>
              </div>
            </div>
            
            {violations && violations.length > 0 && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '2rem', textAlign: 'left' }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>Detailed Violations</h4>
                <div style={{ background: 'var(--background-color)', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: 'var(--surface-color)', borderBottom: '1px solid var(--border-color)' }}>
                        <th style={{ padding: '1rem', fontWeight: 500 }}>Type</th>
                        <th style={{ padding: '1rem', fontWeight: 500 }}>Product</th>
                        <th style={{ padding: '1rem', fontWeight: 500 }}>Expected Position</th>
                        <th style={{ padding: '1rem', fontWeight: 500 }}>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(activeFilter ? violations.filter(v => v.violation_type === activeFilter) : violations).map(v => (
                        <tr key={v.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '1rem' }}>
                            <Badge variant={
                              v.violation_type === 'MISSING_PRODUCT' ? 'warning' :
                              v.violation_type === 'EXTRA_PRODUCT' ? 'success' :
                              v.violation_type === 'MISPLACED_PRODUCT' ? 'danger' : 'info'
                            }>
                              {v.violation_type.replace('_PRODUCT', '')}
                            </Badge>
                          </td>
                          <td style={{ padding: '1rem' }}>
                            <div style={{ fontWeight: 500 }}>{v.expected_name || v.actual_name || 'Unknown Product'}</div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-light)', marginTop: '0.25rem' }}>SKU: {v.expected_sku || v.actual_sku || 'N/A'}</div>
                          </td>
                          <td style={{ padding: '1rem' }}>{v.position}</td>
                          <td style={{ padding: '1rem', color: 'var(--text-light)', fontSize: '0.9rem' }}>{v.details || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(activeFilter && violations.filter(v => v.violation_type === activeFilter).length === 0) && (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-light)' }}>
                      No violations of this type.
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {audit.image_url && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '2rem' }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>Analyzed Image</h4>
                <img src={audit.image_url} alt="Analyzed shelf" style={{ width: '100%', borderRadius: '8px', border: '1px solid var(--border-color)' }} />
              </div>
            )}

            {reviews && reviews.length > 0 && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--border-color)', paddingTop: '2rem', textAlign: 'left' }}>
                <h4 style={{ margin: '0 0 1rem 0' }}>Human Review History</h4>
                <div style={{ background: 'var(--background-color)', padding: '1rem', borderRadius: '8px' }}>
                  {reviews.map(rev => (
                    <div key={rev.id} style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>Initial Prediction</div>
                        <div style={{ fontWeight: 500 }}>
                          {rev.predicted_name || 'Unknown'} 
                          {rev.similarity != null ? ` (${(rev.similarity * 100).toFixed(0)}%)` : ''}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-light)' }}>Final Resolution</div>
                        <div style={{ fontWeight: 500, color: 'var(--primary-color)' }}>
                          {rev.corrected_name || rev.predicted_name || 'Unknown'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AuditResult;
