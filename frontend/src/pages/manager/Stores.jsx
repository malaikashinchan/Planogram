import React, { useState, useEffect } from 'react';
import storeService from '../../services/storeService';
import Table from '../../components/Table/Table';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import EmptyState from '../../components/EmptyState/EmptyState';
import Button from '../../components/Button/Button';
import Modal from '../../components/Modal/Modal';
import Input from '../../components/Input/Input';

const Stores = () => {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedStore, setSelectedStore] = useState(null);

  const [newStoreCode, setNewStoreCode] = useState('');
  const [newStoreName, setNewStoreName] = useState('');
  const [newStoreLocation, setNewStoreLocation] = useState('');
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');

  useEffect(() => {
    const fetchStores = async () => {
      try {
        const data = await storeService.getStores();
        setStores(data);
      } catch (err) {
        setError('Failed to load stores.');
      } finally {
        setLoading(false);
      }
    };
    fetchStores();
  }, []);

  if (loading && stores.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setAdding(true);
    setAddError('');
    try {
      await storeService.createStore({
        code: newStoreCode,
        name: newStoreName,
        address: newStoreLocation
      });
      setIsModalOpen(false);
      setNewStoreCode('');
      setNewStoreName('');
      setNewStoreLocation('');
      setLoading(true);
      const data = await storeService.getStores();
      setStores(data);
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to create store.');
    } finally {
      setAdding(false);
      setLoading(false);
    }
  };

  const toggleStoreStatus = async (store) => {
    try {
      const newStatus = store.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
      await storeService.updateStoreStatus(store.id, newStatus);
      setStores(stores.map(s => s.id === store.id ? { ...s, status: newStatus } : s));
      if (selectedStore && selectedStore.id === store.id) {
        setSelectedStore({ ...selectedStore, status: newStatus });
      }
    } catch (err) {
      alert("Failed to update status.");
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Store Management</h2>
        <Button onClick={() => setIsModalOpen(true)}>+ Add Store</Button>
      </div>
      
      {stores.length === 0 ? (
        <EmptyState message="No stores found." />
      ) : (
        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <Table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Location</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stores.map(store => (
                <tr key={store.id}>
                  <td style={{ fontWeight: 500 }}>{store.name}</td>
                  <td>{store.address || 'N/A'}</td>
                  <td>
                    <Badge variant={store.status === 'ACTIVE' ? 'success' : 'danger'}>
                      {store.status}
                    </Badge>
                  </td>
                  <td>
                    <button 
                      onClick={() => setSelectedStore(store)}
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

      <Modal isOpen={isModalOpen} onClose={() => !adding && setIsModalOpen(false)}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Add New Store</h3>
        <ErrorMessage message={addError} />
        
        <form onSubmit={handleAddSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Store Code</label>
            <Input 
              value={newStoreCode} 
              onChange={e => setNewStoreCode(e.target.value)} 
              placeholder="e.g., STR-001" 
              required 
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Store Name</label>
            <Input 
              value={newStoreName} 
              onChange={e => setNewStoreName(e.target.value)} 
              placeholder="e.g., Downtown Branch" 
              required 
            />
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Address / Location</label>
            <Input 
              value={newStoreLocation} 
              onChange={e => setNewStoreLocation(e.target.value)} 
              placeholder="e.g., 123 Main St, New York" 
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)} disabled={adding}>
              Cancel
            </Button>
            <Button type="submit" disabled={adding}>
              {adding ? 'Creating...' : 'Create Store'}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={!!selectedStore} onClose={() => setSelectedStore(null)}>
        {selectedStore && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem 0' }}>{selectedStore.name}</h3>
                <div style={{ color: 'var(--text-light)', fontSize: '0.9rem' }}>Code: {selectedStore.code}</div>
              </div>
              <Badge variant={selectedStore.status === 'ACTIVE' ? 'success' : 'danger'}>
                {selectedStore.status}
              </Badge>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>Address</div>
              <div style={{ color: 'var(--text-secondary)' }}>{selectedStore.address || 'No address provided'}</div>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>Created At</div>
              <div style={{ color: 'var(--text-secondary)' }}>{new Date(selectedStore.created_at).toLocaleString()}</div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Button 
                variant={selectedStore.status === 'ACTIVE' ? 'danger' : 'success'} 
                onClick={() => toggleStoreStatus(selectedStore)}
              >
                {selectedStore.status === 'ACTIVE' ? 'Deactivate Store' : 'Activate Store'}
              </Button>
              <Button variant="secondary" onClick={() => setSelectedStore(null)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Stores;
