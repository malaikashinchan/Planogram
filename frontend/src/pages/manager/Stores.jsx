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
import MapPicker from '../../components/MapPicker/MapPicker';
import './Stores.css';

const Stores = () => {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedStore, setSelectedStore] = useState(null);

  // --------------------------------------------------
  // New Store form
  // --------------------------------------------------

  const [newStoreCode, setNewStoreCode] = useState('');
  const [newStoreName, setNewStoreName] = useState('');

  const [newStoreLocation, setNewStoreLocation] = useState('');
  const [newStorePincode, setNewStorePincode] = useState('');

  const [newStoreLatitude, setNewStoreLatitude] = useState(null);
  const [newStoreLongitude, setNewStoreLongitude] = useState(null);

  const [mapCenter, setMapCenter] = useState([20.5937, 78.9629]);
  const [mapZoom, setMapZoom] = useState(5);

  const [newStoreLandmark, setNewStoreLandmark] = useState('');
  const [newStoreAddressDetails, setNewStoreAddressDetails] = useState('');

  const [geocoding, setGeocoding] = useState(false);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');

  useEffect(() => {
    if (newStorePincode && newStorePincode.length === 6 && !newStoreLatitude) {
      const fetchPincodeLocation = async () => {
        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/search?postalcode=${newStorePincode}&country=India&format=json`);
          const data = await res.json();
          if (data && data.length > 0) {
            setMapCenter([parseFloat(data[0].lat), parseFloat(data[0].lon)]);
            setMapZoom(12);
          }
        } catch (err) {
          console.error("Geocoding pincode failed", err);
        }
      };
      fetchPincodeLocation();
    }
  }, [newStorePincode, newStoreLatitude]);

  // --------------------------------------------------
  // Fetch stores
  // --------------------------------------------------

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

  // --------------------------------------------------
  // Map location selected
  // --------------------------------------------------

  const handleMapLocationSelect = async (latitude, longitude) => {
    setNewStoreLatitude(latitude);
    setNewStoreLongitude(longitude);

    setGeocoding(true);
    setAddError('');

    try {
      const data = await storeService.reverseGeocode(
        latitude,
        longitude
      );

      setNewStoreLocation(data.address || '');

      setNewStorePincode(data.pincode || '');

    } catch (err) {
      setAddError(
        err.response?.data?.detail || 'Location selected, but address could not be fetched. Please try clicking the map again.'
      );
    } finally {
      setGeocoding(false);
    }
  };

  // --------------------------------------------------
  // Reset Add Store form
  // --------------------------------------------------

  const resetStoreForm = () => {
    setNewStoreCode('');
    setNewStoreName('');
    setNewStoreLocation('');
    setNewStorePincode('');
    setNewStoreLatitude(null);
    setNewStoreLongitude(null);
    setMapCenter([20.5937, 78.9629]);
    setMapZoom(5);
    setNewStoreLandmark('');
    setNewStoreAddressDetails('');
    setAddError('');
    setGeocoding(false);
  };

  // --------------------------------------------------
  // Create Store
  // --------------------------------------------------

  const handleAddSubmit = async (e) => {
    e.preventDefault();

    setAdding(true);
    setAddError('');

    try {
      await storeService.createStore({
        code: newStoreCode,
        name: newStoreName,

        address: newStoreLocation,
        pincode: newStorePincode,

        latitude: newStoreLatitude,
        longitude: newStoreLongitude,

        landmark: newStoreLandmark,
        address_details: newStoreAddressDetails,
      });

      setIsModalOpen(false);
      resetStoreForm();

      setLoading(true);

      const data = await storeService.getStores();
      setStores(data);

    } catch (err) {
      setAddError(
        err.response?.data?.detail ||
        'Failed to create store.'
      );
    } finally {
      setAdding(false);
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // Toggle Store Status
  // --------------------------------------------------

  const toggleStoreStatus = async (store) => {
    try {
      const newStatus =
        store.status === 'ACTIVE'
          ? 'INACTIVE'
          : 'ACTIVE';

      await storeService.updateStoreStatus(
        store.id,
        newStatus
      );

      setStores(
        stores.map((s) =>
          s.id === store.id
            ? { ...s, status: newStatus }
            : s
        )
      );

      if (
        selectedStore &&
        selectedStore.id === store.id
      ) {
        setSelectedStore({
          ...selectedStore,
          status: newStatus,
        });
      }

    } catch (err) {
      alert('Failed to update status.');
    }
  };

  // --------------------------------------------------
  // Delete Store
  // --------------------------------------------------

  const handleDeleteStore = async (store) => {
    if (!window.confirm(`Are you sure you want to permanently delete ${store.name}?`)) {
      return;
    }
    
    try {
      await storeService.deleteStore(store.id);
      setStores(stores.filter(s => s.id !== store.id));
      setSelectedStore(null);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete store.');
    }
  };

  // --------------------------------------------------
  // Loading / Error
  // --------------------------------------------------

  if (loading && stores.length === 0) {
    return <Spinner />;
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div>

      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}
      >
        <h2>Store Management</h2>

        <Button
          onClick={() => {
            resetStoreForm();
            setIsModalOpen(true);
          }}
        >
          + Add Store
        </Button>
      </div>

      {/* Store Table */}
      {stores.length === 0 ? (
        <EmptyState message="No stores found." />
      ) : (
        <div
          style={{
            background: 'var(--surface-color)',
            padding: '1.5rem',
            borderRadius: '8px',
            boxShadow: 'var(--card-shadow)'
          }}
        >
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
              {stores.map((store) => (
                <tr key={store.id}>

                  <td style={{ fontWeight: 500 }}>
                    {store.name}
                  </td>

                  <td>
                    {store.address || 'N/A'}
                  </td>

                  <td>
                    <Badge
                      variant={
                        store.status === 'ACTIVE'
                          ? 'success'
                          : 'danger'
                      }
                    >
                      {store.status}
                    </Badge>
                  </td>

                  <td>
                    <button
                      onClick={() =>
                        setSelectedStore(store)
                      }
                      style={{
                        color: '#007bff',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0
                      }}
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

      {/* ==================================================
          ADD STORE MODAL
          ================================================== */}

      <Modal
        isOpen={isModalOpen}
        onClose={() =>
          !adding && setIsModalOpen(false)
        }
      >

        <h3
          style={{
            marginTop: 0,
            marginBottom: '1.5rem'
          }}
        >
          Add New Store
        </h3>

        <ErrorMessage message={addError} />

        <form onSubmit={handleAddSubmit}>

          {/* Store Code */}
          <div style={{ marginBottom: '1rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Store Code
            </label>

            <Input
              value={newStoreCode}
              onChange={(e) =>
                setNewStoreCode(e.target.value)
              }
              placeholder="e.g., STR-001"
              required
            />
          </div>

          {/* Store Name */}
          <div style={{ marginBottom: '1rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Store Name
            </label>

            <Input
              value={newStoreName}
              onChange={(e) =>
                setNewStoreName(e.target.value)
              }
              placeholder="e.g., Downtown Branch"
              required
            />
          </div>

          {/* Pincode Moved Above Map */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Enter Pincode to Zoom Map
            </label>

            <Input
              value={newStorePincode}
              onChange={(e) =>
                setNewStorePincode(e.target.value)
              }
              placeholder="e.g., 400001"
            />
          </div>

          {/* Map */}
          <div style={{ marginBottom: '1.5rem' }}>

            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Pinpoint Location on Map
            </label>

            <MapPicker
              latitude={newStoreLatitude}
              longitude={newStoreLongitude}
              mapCenter={mapCenter}
              mapZoom={mapZoom}
              onLocationSelect={
                handleMapLocationSelect
              }
            />

            {geocoding && (
              <div
                style={{
                  marginTop: '0.5rem',
                  fontSize: '0.85rem',
                  color: 'var(--text-muted)'
                }}
              >
                Fetching address...
              </div>
            )}

          </div>

          {/* Address */}
          <div style={{ marginBottom: '1rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Address
            </label>

            <Input
              value={newStoreLocation}
              onChange={(e) =>
                setNewStoreLocation(e.target.value)
              }
              placeholder="Address"
            />
          </div>

          {/* Shop / Building Details */}
          <div style={{ marginBottom: '1rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Shop / Building No.
            </label>

            <Input
              value={newStoreAddressDetails}
              onChange={(e) =>
                setNewStoreAddressDetails(
                  e.target.value
                )
              }
              placeholder="e.g., Shop 12, Building A"
            />
          </div>

          {/* Landmark */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label
              style={{
                display: 'block',
                marginBottom: '0.5rem',
                fontWeight: 500
              }}
            >
              Landmark
            </label>

            <Input
              value={newStoreLandmark}
              onChange={(e) =>
                setNewStoreLandmark(e.target.value)
              }
              placeholder="e.g., Near City Mall"
            />
          </div>

          {/* Coordinates */}
          {newStoreLatitude !== null &&
            newStoreLongitude !== null && (
              <div
                style={{
                  marginBottom: '1.5rem',
                  padding: '0.75rem',
                  background: 'var(--bg-color-alt)',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  color: 'var(--text-muted)'
                }}
              >
                Location selected: {newStoreLatitude.toFixed(6)},
                {' '}
                {newStoreLongitude.toFixed(6)}
              </div>
            )}

          {/* Buttons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '1rem'
            }}
          >

            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                setIsModalOpen(false)
              }
              disabled={adding}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              disabled={adding || geocoding}
            >
              {adding
                ? 'Creating...'
                : 'Create Store'}
            </Button>

          </div>

        </form>

      </Modal>

      {/* ==================================================
          STORE DETAILS MODAL
          ================================================== */}

      <Modal
        isOpen={!!selectedStore}
        onClose={() =>
          setSelectedStore(null)
        }
      >

        {selectedStore && (
          <div>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '1.5rem',
                borderBottom:
                  '1px solid var(--border-color)',
                paddingBottom: '1rem'
              }}
            >

              <div>
                <h3
                  style={{
                    margin: '0 0 0.5rem 0'
                  }}
                >
                  {selectedStore.name}
                </h3>

                <div
                  style={{
                    color: 'var(--text-light)',
                    fontSize: '0.9rem'
                  }}
                >
                  Code: {selectedStore.code}
                </div>
              </div>

              <Badge
                variant={
                  selectedStore.status === 'ACTIVE'
                    ? 'success'
                    : 'danger'
                }
              >
                {selectedStore.status}
              </Badge>

            </div>

            {/* Address */}
            <div style={{ marginBottom: '1rem' }}>
              <div
                style={{
                  fontWeight: 500,
                  marginBottom: '0.25rem'
                }}
              >
                Address
              </div>

              <div
                style={{
                  color: 'var(--text-secondary)'
                }}
              >
                {selectedStore.address ||
                  'No address provided'}
              </div>
            </div>

            {/* Pincode */}
            <div style={{ marginBottom: '1rem' }}>
              <div
                style={{
                  fontWeight: 500,
                  marginBottom: '0.25rem'
                }}
              >
                Pincode
              </div>

              <div
                style={{
                  color: 'var(--text-secondary)'
                }}
              >
                {selectedStore.pincode || 'N/A'}
              </div>
            </div>

            {/* Shop / Building */}
            <div style={{ marginBottom: '1rem' }}>
              <div
                style={{
                  fontWeight: 500,
                  marginBottom: '0.25rem'
                }}
              >
                Shop / Building No.
              </div>

              <div
                style={{
                  color: 'var(--text-secondary)'
                }}
              >
                {selectedStore.address_details ||
                  'N/A'}
              </div>
            </div>

            {/* Landmark */}
            <div style={{ marginBottom: '1rem' }}>
              <div
                style={{
                  fontWeight: 500,
                  marginBottom: '0.25rem'
                }}
              >
                Landmark
              </div>

              <div
                style={{
                  color: 'var(--text-secondary)'
                }}
              >
                {selectedStore.landmark || 'N/A'}
              </div>
            </div>

            {/* Coordinates */}
            {selectedStore.latitude !== null &&
              selectedStore.longitude !== null && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <div
                    style={{
                      fontWeight: 500,
                      marginBottom: '0.25rem'
                    }}
                  >
                    Coordinates
                  </div>

                  <div
                    style={{
                      color: 'var(--text-secondary)'
                    }}
                  >
                    {selectedStore.latitude.toFixed(6)},
                    {' '}
                    {selectedStore.longitude.toFixed(6)}
                  </div>
                </div>
              )}

            {/* Created At */}
            <div style={{ marginBottom: '2rem' }}>
              <div
                style={{
                  fontWeight: 500,
                  marginBottom: '0.25rem'
                }}
              >
                Created At
              </div>

              <div
                style={{
                  color: 'var(--text-secondary)'
                }}
              >
                {new Date(
                  selectedStore.created_at
                ).toLocaleString()}
              </div>
            </div>

            {/* Actions */}
            <div
              style={{
                display: 'flex',
                gap: '1rem',
                width: '100%',
                marginTop: '1rem'
              }}
            >
              <Button
                variant={
                  selectedStore.status === 'ACTIVE'
                    ? 'warning'
                    : 'success'
                }
                style={{ flex: 1 }}
                onClick={() =>
                  toggleStoreStatus(selectedStore)
                }
              >
                {selectedStore.status === 'ACTIVE'
                  ? 'Deactivate'
                  : 'Activate'}
              </Button>
              
              <Button
                variant="danger"
                style={{ flex: 1 }}
                onClick={() => handleDeleteStore(selectedStore)}
              >
                Delete
              </Button>

              <Button
                variant="secondary"
                style={{ flex: 1 }}
                onClick={() =>
                  setSelectedStore(null)
                }
              >
                Close
              </Button>
            </div>

          </div>
        )}

      </Modal>

    </div>
  );
};

export default Stores;