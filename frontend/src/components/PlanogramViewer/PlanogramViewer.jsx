import React, { useState, useEffect } from 'react';
import api from '../../api/api';
import Spinner from '../Spinner/Spinner';
import ErrorMessage from '../ErrorMessage/ErrorMessage';
import styles from './PlanogramViewer.module.css';
import { Layers } from 'lucide-react';

const PlanogramViewer = ({ planogramId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(null);

  useEffect(() => {
    const fetchPlanogram = async () => {
      try {
        setLoading(true);
        // Get all versions for this planogram, then grab the latest
        const response = await api.get(`/planograms/${planogramId}/versions`);
        const versions = response.data;
        
        if (!versions || versions.length === 0) {
          setError('No layout defined for this planogram.');
          return;
        }

        // Usually the last element is the latest version
        const latestVersion = versions[versions.length - 1];
        setVersion(latestVersion);
      } catch (err) {
        console.error(err);
        setError('Failed to load planogram layout.');
      } finally {
        setLoading(false);
      }
    };

    if (planogramId) {
      fetchPlanogram();
    }
  }, [planogramId]);

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!version) return null;

  // Group positions by shelf_id
  const shelves = {};
  version.positions?.forEach(pos => {
    if (!shelves[pos.shelf_id]) {
      shelves[pos.shelf_id] = [];
    }
    shelves[pos.shelf_id].push(pos);
  });

  // Sort shelves descending (top shelf = highest ID or lowest ID? Usually shelf 1 is bottom or top. Let's assume shelf 1 is top and sort ascending)
  const sortedShelfIds = Object.keys(shelves).map(Number).sort((a, b) => a - b);

  return (
    <div className={styles.viewerContainer}>
      <div className={styles.header}>
        <Layers size={20} className={styles.icon} />
        <h3 className={styles.title}>Target Layout (Version {version.version_number})</h3>
      </div>
      
      {sortedShelfIds.length === 0 ? (
        <p className={styles.emptyText}>No products mapped to shelves yet.</p>
      ) : (
        <div className={styles.shelvesWrapper}>
          {sortedShelfIds.map(shelfId => {
            // Sort products by position (left to right)
            const positions = shelves[shelfId].sort((a, b) => a.position - b.position);
            
            return (
              <div key={shelfId} className={styles.shelfRow}>
                <div className={styles.shelfLabel}>Shelf {shelfId}</div>
                <div className={styles.shelfItems}>
                  {positions.map(pos => (
                    <div key={pos.id} className={styles.productItem}>
                      <div className={styles.productColorIndicator}></div>
                      <div className={styles.productDetails}>
                        <span className={styles.productName}>{pos.product?.name || pos.product?.sku_code || 'Unknown Product'}</span>
                        <span className={styles.productBrand}>{pos.product?.brand || 'Generic'}</span>
                      </div>
                      <div className={styles.positionBadge}>Pos {pos.position}</div>
                    </div>
                  ))}
                </div>
                <div className={styles.shelfBoard}></div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PlanogramViewer;
