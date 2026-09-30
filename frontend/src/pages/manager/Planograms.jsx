// import React, { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
// import planogramService from '../../services/planogramService';
// import storeService from '../../services/storeService';
// import Table from '../../components/Table/Table';
// import Button from '../../components/Button/Button';
// import Modal from '../../components/Modal/Modal';
// import Input from '../../components/Input/Input';
// import Select from '../../components/Select/Select';
// import Spinner from '../../components/Spinner/Spinner';
// import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
// import EmptyState from '../../components/EmptyState/EmptyState';

// const Planograms = () => {
//   const navigate = useNavigate();
//   const [planograms, setPlanograms] = useState([]);
//   const [stores, setStores] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState('');

//   // Upload State
//   const [isUploadOpen, setIsUploadOpen] = useState(false);
//   const [uploadName, setUploadName] = useState('');
//   const [uploadStoreId, setUploadStoreId] = useState('');
//   const [uploadFile, setUploadFile] = useState(null);
//   const [uploading, setUploading] = useState(false);
//   const [uploadError, setUploadError] = useState('');
//   const [uploadSuccess, setUploadSuccess] = useState('');

//   const fetchPlanogramsAndStores = async () => {
//     setLoading(true);
//     try {
//       const [planoData, storeData] = await Promise.all([
//         planogramService.getPlanograms(),
//         storeService.getStores()
//       ]);
//       setPlanograms(planoData);
//       setStores(storeData);
//     } catch (err) {
//       setError('Failed to load planograms.');
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchPlanogramsAndStores();
//   }, []);

//   const handleUploadSubmit = async (e) => {
//     e.preventDefault();
//     if (!uploadFile) {
//       setUploadError("Please select a file to upload.");
//       return;
//     }
//     setUploadError('');
//     setUploadSuccess('');
//     setUploading(true);

//     try {
//       await planogramService.uploadPlanogram(uploadName, uploadStoreId, uploadFile);
//       setUploadSuccess("Planogram uploaded successfully!");
//       setUploadName('');
//       setUploadFile(null);

//       // Refresh the list
//       await fetchPlanogramsAndStores();

//       // Auto close modal after success
//       setTimeout(() => setIsUploadOpen(false), 2000);
//     } catch (err) {
//       setUploadError(err.response?.data?.detail || "Upload failed. Please ensure it's a valid CSV/Excel file.");
//     } finally {
//       setUploading(false);
//     }
//   };

//   const handleDelete = async (id) => {
//     if (window.confirm("Are you sure you want to delete this planogram? This action cannot be undone.")) {
//       try {
//         await planogramService.deletePlanogram(id);
//         await fetchPlanogramsAndStores();
//       } catch (err) {
//         alert("Failed to delete planogram.");
//       }
//     }
//   };

//   if (loading && planograms.length === 0) return <Spinner />;
//   if (error) return <ErrorMessage message={error} />;

//   return (
//     <div>
//       <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
//         <h2>Planogram Management</h2>
//         <Button onClick={() => {
//           setIsUploadOpen(true);
//           setUploadSuccess('');
//           setUploadError('');
//         }}>
//           Upload Planogram
//         </Button>
//       </div>

//       {planograms.length === 0 ? (
//         <EmptyState message="No planograms have been uploaded yet." />
//       ) : (
//         <div style={{ background: 'var(--surface-color)', padding: '1.5rem', borderRadius: '8px', boxShadow: 'var(--card-shadow)' }}>
//           <Table>
//             <thead>
//               <tr>
//                 <th>Name</th>
//                 <th>Store</th>
//                 <th>Positions</th>
//                 <th>Created At</th>
//                 <th>Actions</th>
//               </tr>
//             </thead>
//             <tbody>
//               {planograms.map(plano => (
//                 <tr key={plano.id}>
//                   <td style={{ fontWeight: 500 }}>{plano.name}</td>
//                   <td>{plano.store?.name || 'N/A'}</td>
//                   <td>{plano.positions_count || 0}</td>
//                   <td>{new Date(plano.created_at).toLocaleDateString()}</td>
//                   <td>
//                     <button 
//                       onClick={() => handleDelete(plano.id)}
//                       style={{ color: 'var(--danger-color)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
//                     >
//                       Delete
//                     </button>
//                   </td>
//                 </tr>
//               ))}
//             </tbody>
//           </Table>
//         </div>
//       )}

//       <Modal isOpen={isUploadOpen} onClose={() => !uploading && setIsUploadOpen(false)}>
//         <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Upload Planogram</h3>
//         <ErrorMessage message={uploadError} />
//         {uploadError && uploadError.includes("Products not found") && (
//           <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
//             <Button variant="secondary" onClick={() => navigate('/manager/products')}>
//               Go to Product Master to add missing products
//             </Button>
//           </div>
//         )}
//         {uploadSuccess && <div style={{ color: 'green', padding: '1rem', background: '#e6ffe6', borderRadius: '4px', marginBottom: '1rem' }}>{uploadSuccess}</div>}

//         <form onSubmit={handleUploadSubmit}>
//           <div style={{ marginBottom: '1rem' }}>
//             <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Planogram Name</label>
//             <Input 
//               value={uploadName} 
//               onChange={e => setUploadName(e.target.value)} 
//               placeholder="e.g., Summer Endcap 2024" 
//               required 
//             />
//           </div>
//           <div style={{ marginBottom: '1rem' }}>
//             <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Target Store</label>
//             <Select 
//               value={uploadStoreId} 
//               onChange={e => setUploadStoreId(e.target.value)}
//               required
//             >
//               <option value="">-- Select Store --</option>
//               {stores.map(s => (
//                 <option key={s.id} value={s.id}>{s.name}</option>
//               ))}
//             </Select>
//           </div>
//           <div style={{ marginBottom: '1.5rem' }}>
//             <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>File (CSV/XLS/XLSX)</label>
//             <input 
//               type="file" 
//               accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel"
//               onChange={e => setUploadFile(e.target.files[0])}
//               required
//             />
//           </div>
//           <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
//             <Button type="button" variant="secondary" onClick={() => setIsUploadOpen(false)} disabled={uploading}>
//               Cancel
//             </Button>
//             <Button type="submit" disabled={uploading}>
//               {uploading ? 'Uploading...' : 'Upload'}
//             </Button>
//           </div>
//         </form>
//       </Modal>
//     </div>
//   );
// };

// export default Planograms;

import React, { useState, useEffect, useRef } from 'react';
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

  // Preview State
  const [parsedPreview, setParsedPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const fileInputRef = useRef(null);

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

  // Handle file selection + preview
  const handleFileChange = async (e) => {
    const file = e.target.files[0];

    setUploadFile(file);
    setUploadError('');
    setUploadSuccess('');
    setParsedPreview(null);

    if (!file) return;

    setPreviewing(true);

    try {
      const result = await planogramService.previewPlanogram(file);
      setParsedPreview(result);
    } catch (err) {
      setUploadError(
        err.response?.data?.detail || 'Preview failed. Please check the file format and column order.'
      );

      setUploadFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } finally {
      setPreviewing(false);
    }
  };

  // Final upload only after preview confirmation
  const handleUploadSubmit = async () => {
    if (!uploadFile || !parsedPreview) return;

    setUploading(true);
    setUploadError('');
    setUploadSuccess('');

    try {
      await planogramService.uploadPlanogram(
        uploadName,
        uploadStoreId,
        uploadFile
      );

      setUploadSuccess('Planogram uploaded successfully!');

      await fetchPlanogramsAndStores();

      setTimeout(() => {
        setIsUploadOpen(false);
        setUploadSuccess('');
        setUploadName('');
        setUploadStoreId('');
        setUploadFile(null);
        setParsedPreview(null);

        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }, 2000);

    } catch (err) {
      setUploadError(
        err.response?.data?.detail ||
        "Upload failed. Please ensure the file is valid and all referenced SKUs exist in Product Master."
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    if (
      window.confirm(
        "Are you sure you want to delete this planogram? This action cannot be undone."
      )
    ) {
      try {
        await planogramService.deletePlanogram(id);
        await fetchPlanogramsAndStores();
      } catch (err) {
        alert("Failed to delete planogram.");
      }
    }
  };

  const handleCloseUploadModal = () => {
    if (uploading || previewing) return;

    setIsUploadOpen(false);
    setUploadFile(null);
    setParsedPreview(null);
    setUploadError('');
    setUploadSuccess('');
    setUploadName('');
    setUploadStoreId('');

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (loading && planograms.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}
      >
        <h2>Planogram Management</h2>

        <Button
          onClick={() => {
            setIsUploadOpen(true);
            setUploadSuccess('');
            setUploadError('');
            setParsedPreview(null);
          }}
        >
          Upload Planogram
        </Button>
      </div>

      {planograms.length === 0 ? (
        <EmptyState message="No planograms have been uploaded yet." />
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
                <th>Store</th>
                <th>Positions</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {planograms.map(plano => (
                <tr key={plano.id}>
                  <td style={{ fontWeight: 500 }}>
                    {plano.name}
                  </td>

                  <td>
                    {plano.store?.name || 'N/A'}
                  </td>

                  <td>
                    {plano.positions_count || 0}
                  </td>

                  <td>
                    {new Date(plano.created_at).toLocaleDateString()}
                  </td>

                  <td>
                    <button
                      onClick={() => handleDelete(plano.id)}
                      style={{
                        color: 'var(--danger-color)',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0
                      }}
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

      {/* Upload Planogram Modal */}
      <Modal
        isOpen={isUploadOpen}
        onClose={handleCloseUploadModal}
      >
        <h3
          style={{
            marginTop: 0,
            marginBottom: '1.5rem'
          }}
        >
          Upload Planogram
        </h3>

        {uploadSuccess ? (
          <div
            style={{
              textAlign: 'center',
              padding: '2rem',
              color: 'var(--success-color)'
            }}
          >
            <div
              style={{
                fontSize: '3rem',
                marginBottom: '1rem'
              }}
            >
              ✓
            </div>

            <h3>{uploadSuccess}</h3>
          </div>
        ) : (
          <>
            <ErrorMessage message={uploadError} />

            {uploadError &&
              uploadError.includes("Products not found") && (
                <div
                  style={{
                    marginBottom: '1.5rem',
                    textAlign: 'center'
                  }}
                >
                  <Button
                    variant="secondary"
                    onClick={() =>
                      navigate('/manager/products')
                    }
                  >
                    Go to Product Master to add missing products
                  </Button>
                </div>
              )}

            {/* Planogram upload instructions */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div
                style={{
                  background: 'var(--primary-light)',
                  padding: '1rem',
                  borderRadius: '4px',
                  marginBottom: '1rem',
                  borderLeft: '4px solid var(--primary-color)'
                }}
              >
                <strong>Important:</strong>{' '}
                We map columns by their exact order, regardless of
                what the column is named.

                <br />

                Your file <strong>must</strong> be in this exact
                sequence:

                <br />

                <code>
                  1. Planogram ID | 2. Version | 3. Store ID |
                  4. Shelf ID | 5. Position | 6. SKU ID
                </code>
              </div>

              {/* File input */}
              <div
                style={{
                  background: 'var(--background-color)',
                  padding: '1rem',
                  borderRadius: '4px',
                  border: '1px dashed var(--border-color)',
                  textAlign: 'center'
                }}
              >
                <input
                  type="file"
                  accept=".csv,.xls,.xlsx,.json"
                  onChange={handleFileChange}
                  ref={fileInputRef}
                  style={{
                    display: 'block',
                    width: '100%',
                    cursor: 'pointer'
                  }}
                  disabled={previewing || uploading}
                />

                {previewing && (
                  <div
                    style={{
                      marginTop: '0.75rem',
                      color: 'var(--text-secondary)'
                    }}
                  >
                    Reading file and preparing preview...
                  </div>
                )}
              </div>
            </div>

            {/* Planogram Name */}
            <div style={{ marginBottom: '1rem' }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: 500
                }}
              >
                Planogram Name
              </label>

              <Input
                value={uploadName}
                onChange={e =>
                  setUploadName(e.target.value)
                }
                placeholder="e.g., Summer Endcap 2024"
                required
              />
            </div>

            {/* Target Store */}
            <div style={{ marginBottom: '1rem' }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: '0.5rem',
                  fontWeight: 500
                }}
              >
                Target Store
              </label>

              <Select
                value={uploadStoreId}
                onChange={e =>
                  setUploadStoreId(e.target.value)
                }
                required
              >
                <option value="">
                  -- Select Store --
                </option>

                {stores.map(s => (
                  <option
                    key={s.id}
                    value={s.id}
                  >
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>

            {/* Preview */}
            {parsedPreview && (
              <div style={{ marginBottom: '1.5rem' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem'
                  }}
                >
                  <span style={{ fontWeight: 500 }}>
                    Previewing {parsedPreview.preview.length} of{' '}
                    {parsedPreview.totalRows} positions
                  </span>
                </div>

                <div
                  style={{
                    overflowX: 'auto',
                    border: '1px solid var(--border-color)',
                    borderRadius: '4px'
                  }}
                >
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '0.85rem'
                    }}
                  >
                    <thead
                      style={{
                        background: 'var(--background-color)',
                        borderBottom:
                          '1px solid var(--border-color)'
                      }}
                    >
                      <tr>
                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          Planogram ID
                        </th>

                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          Version
                        </th>

                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          Store ID
                        </th>

                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          Shelf ID
                        </th>

                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          Position
                        </th>

                        <th
                          style={{
                            padding: '0.5rem',
                            textAlign: 'left'
                          }}
                        >
                          SKU ID
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {parsedPreview.preview.map((row, i) => (
                        <tr
                          key={i}
                          style={{
                            borderBottom:
                              '1px solid var(--border-color)'
                          }}
                        >
                          <td style={{ padding: '0.5rem' }}>
                            {row.planogram_id}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            {row.version}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            {row.store_id}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            {row.shelf_id}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            {row.position}
                          </td>

                          <td style={{ padding: '0.5rem' }}>
                            {row.sku_id}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Existing upload form */}
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
                onClick={handleCloseUploadModal}
                disabled={uploading || previewing}
              >
                Cancel
              </Button>

              <Button
                onClick={handleUploadSubmit}
                disabled={
                  !parsedPreview ||
                  previewing ||
                  uploading ||
                  !uploadName ||
                  !uploadStoreId
                }
              >
                {uploading
                  ? 'Uploading...'
                  : 'Confirm Upload'}
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
};

export default Planograms;