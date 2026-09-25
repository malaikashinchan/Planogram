import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import dashboardService from '../../services/dashboardService';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import Button from '../../components/Button/Button';
import styles from './Dashboard.module.css';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, trendsData, modelData] = await Promise.all([
          dashboardService.getAuditStatistics(30),
          dashboardService.getComplianceTrends(30),
          dashboardService.getModelStatus()
        ]);
        setStats(statsData);
        setTrends(trendsData.trends || []);
        setModelStatus(modelData);
      } catch (err) {
        setError('Failed to load dashboard data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!stats) return null;

  return (
    <div className={styles.dashboard}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.5rem' }}>
        <Button onClick={() => navigate('/manager/planograms')}>
          + Upload Planogram
        </Button>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <span className={styles.statTitle}>Total Audits (7d)</span>
          <span className={styles.statValue}>{stats.total_audits_last_7_days || 0}</span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statTitle}>Avg Compliance</span>
          <span className={styles.statValue}>
            {stats.average_compliance_score != null ? `${(stats.average_compliance_score * 100).toFixed(1)}%` : 'N/A'}
          </span>
        </div>
        <div className={styles.statCard}>
          <span className={styles.statTitle}>Pending Reviews</span>
          <span className={styles.statValue}>{stats.status_breakdown?.PENDING_REVIEW || 0}</span>
        </div>
      </div>

      <div className={styles.chartsGrid}>
        <div className={styles.chartCard}>
          <h3>Compliance Trend (30 Days)</h3>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e9ecef" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  tick={{ fill: '#6c757d', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  domain={[0, 100]} 
                  tickFormatter={(val) => `${val}%`}
                  tick={{ fill: '#6c757d', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip 
                  formatter={(value) => [`${value.toFixed(1)}%`, 'Compliance']}
                  labelFormatter={(label) => new Date(label).toLocaleDateString()}
                />
                <Line 
                  type="monotone" 
                  dataKey="average_compliance" 
                  stroke="#007bff" 
                  strokeWidth={3}
                  dot={{ r: 4, strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                  connectNulls={false} 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={styles.mlStatusCard}>
          <h3>ML Model Status</h3>
          {modelStatus && (
            <div>
              <div className={styles.statusItem}>
                <span style={{ color: '#6c757d' }}>Current Version</span>
                <span style={{ fontWeight: 500 }}>{modelStatus.active_version}</span>
              </div>
              <div className={styles.statusItem}>
                <span style={{ color: '#6c757d' }}>Status</span>
                <Badge variant={modelStatus.is_training ? 'warning' : 'success'}>
                  {modelStatus.is_training ? 'TRAINING' : 'IDLE'}
                </Badge>
              </div>
              <div className={styles.statusItem}>
                <span style={{ color: '#6c757d' }}>Training Samples</span>
                <span style={{ fontWeight: 500 }}>{modelStatus.pending_training_samples} new</span>
              </div>
              <div className={styles.statusItem}>
                <span style={{ color: '#6c757d' }}>Last Training</span>
                <span style={{ fontWeight: 500 }}>
                  {modelStatus.last_training_date ? new Date(modelStatus.last_training_date).toLocaleDateString() : 'Never'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
