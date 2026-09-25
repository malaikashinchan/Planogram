import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import planogramService from '../../services/planogramService';
import storeService from '../../services/storeService';
import Table from '../../components/Table/Table';
import Button from '../../components/Button/Button';
import Modal from '../../components/Modal/Modal';
import Input from '../../components/Input/Input';
import Select from '../../components/Select/Select';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import EmptyState from '../../components/EmptyState/EmptyState';

const Planograms = () => {
  const navigate = useNavigate();
  const [planograms, setPlanograms] = useState([]);
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Upload State
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadStoreId, setUploadStoreId] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  const fetchPlanogramsAndStores = async () => {
    setLoading(true);
    try {
      const [planoData, storeData] = await Promise.all([
        planogramService.getPlanograms(),
        storeService.getStores()
      ]);
      setPlanograms(planoData);
      setStores(storeData);
    } catch (err) {
      setError('Failed to load planograms.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlanogramsAndStores();
  }, []);

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a file to upload.");
      return;
    }
    setUploadError('');
    setUploadSuccess('');
    setUploading(true);

    try {
      await planogramService.uploadPlanogram(uploadName, uploadStoreId, uploadFile);
      setUploadSuccess("Planogram uploaded successfully!");
      setUploadName('');
      setUploadFile(null);
      
      // Refresh the list
      await fetchPlanogramsAndStores();
      
      // Auto close modal after success
      setTimeout(() => setIsUploadOpen(false), 2000);
    } catch (err) {
      setUploadError(err.response?.data?.detail || "Upload failed. Please ensure it's a valid CSV/Excel file.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this planogram? This action cannot be undone.")) {
      try {
        await planogramService.deletePlanogram(id);
        await fetchPlanogramsAndStores();
      } catch (err) {
        alert("Failed to delete planogram.");
      }
    }
  };

  if (loading && planograms.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Planogram Management</h2>
        <Button onClick={() => {
          setIsUploadOpen(true);
          setUploadSuccess('');
          setUploadError('');
        }}>
          Upload Planogram
        </Button>
      </div>

      {planograms.length === 0 ? (
        <EmptyState message="No planograms have been uploaded yet." />
      ) : (
        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <Table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Store</th>
                <th>Positions</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {planograms.map(plano => (
                <tr key={plano.id}>
                  <td style={{ fontWeight: 500 }}>{plano.name}</td>
                  <td>{plano.store?.name || 'N/A'}</td>
                  <td>{plano.positions_count || 0}</td>
                  <td>{new Date(plano.created_at).toLocaleDateString()}</td>
                  <td>
                    <button 
                      onClick={() => handleDelete(plano.id)}
                      style={{ color: 'var(--danger-color)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <Modal isOpen={isUploadOpen} onClose={() => !uploading && setIsUploadOpen(false)}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Upload Planogram</h3>
        <ErrorMessage message={uploadError} />
        {uploadError && uploadError.includes("Products not found") && (
          <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
            <Button variant="secondary" onClick={() => navigate('/manager/products')}>
              Go to Product Master to add missing products
            </Button>
          </div>
        )}
        {uploadSuccess && <div style={{ color: 'green', padding: '1rem', background: '#e6ffe6', borderRadius: '4px', marginBottom: '1rem' }}>{uploadSuccess}</div>}
        
        <form onSubmit={handleUploadSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Planogram Name</label>
            <Input 
              value={uploadName} 
              onChange={e => setUploadName(e.target.value)} 
              placeholder="e.g., Summer Endcap 2024" 
              required 
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Target Store</label>
            <Select 
              value={uploadStoreId} 
              onChange={e => setUploadStoreId(e.target.value)}
              required
            >
              <option value="">-- Select Store --</option>
              {stores.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>File (CSV/XLS/XLSX)</label>
            <input 
              type="file" 
              accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
              onChange={e => setUploadFile(e.target.files[0])}
              required
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
            <Button type="button" variant="secondary" onClick={() => setIsUploadOpen(false)} disabled={uploading}>
              Cancel
            </Button>
            <Button type="submit" disabled={uploading}>
              {uploading ? 'Uploading...' : 'Upload'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default Planograms;
