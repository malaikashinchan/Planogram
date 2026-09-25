import React, { useState, useEffect } from 'react';
import reviewService from '../../services/reviewService';
import productService from '../../services/productService';
import Table from '../../components/Table/Table';
import Button from '../../components/Button/Button';
import Modal from '../../components/Modal/Modal';
import Input from '../../components/Input/Input';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import Badge from '../../components/Badge/Badge';
import EmptyState from '../../components/EmptyState/EmptyState';

const Reviews = () => {
  const [reviews, setReviews] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Resolution state
  const [selectedReview, setSelectedReview] = useState(null);
  const [resolutionType, setResolutionType] = useState('existing'); // 'existing' or 'new'
  const [selectedProductId, setSelectedProductId] = useState('');
  const [newProductName, setNewProductName] = useState('');
  const [newProductBrand, setNewProductBrand] = useState('');
  const [newProductCategory, setNewProductCategory] = useState('');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState('');
  const [resolveSuccess, setResolveSuccess] = useState('');

  const fetchReviewsAndProducts = async () => {
    try {
      const [reviewData, productData] = await Promise.all([
        reviewService.getPendingReviews(),
        productService.getProducts(0, 100)
      ]);
      setReviews(reviewData);
      setProducts(productData);
    } catch (err) {
      setError('Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviewsAndProducts();
  }, []);

  const handleResolve = async (e) => {
    e.preventDefault();
    if (resolutionType === 'existing' && !selectedProductId) {
      setResolveError("Please select a product");
      return;
    }
    if (resolutionType === 'new' && !newProductName) {
      setResolveError("New product name is required");
      return;
    }

    setResolving(true);
    setResolveError('');
    setResolveSuccess('');

    try {
      await reviewService.resolveReview(selectedReview.id, {
        corrected_product_id: resolutionType === 'existing' ? selectedProductId : null,
        is_new_product: resolutionType === 'new',
        new_product_name: newProductName,
        new_product_brand: newProductBrand,
        new_product_category: newProductCategory
      });
      
      setResolveSuccess("Review resolved ✓");
      
      setTimeout(async () => {
        setSelectedReview(null);
        setResolveSuccess('');
        setResolving(false);
        // Refresh queue
        setLoading(true);
        await fetchReviewsAndProducts();
      }, 1500);

    } catch (err) {
      setResolveError(err.response?.data?.detail || "Failed to resolve review.");
      setResolving(false);
    }
  };

  const getProductName = (id) => {
    if (!id) return "Unknown";
    const prod = products.find(p => p.id === id);
    return prod ? `${prod.sku_code} - ${prod.name}` : "Unknown";
  };

  const filteredProducts = products.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    p.sku_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading && reviews.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Review Queue</h2>
      </div>

      {reviews.length === 0 ? (
        <EmptyState message="No pending reviews. The queue is completely empty!" />
      ) : (
        <div style={{ background: 'var(--surface-color)', padding: '1.5rem', borderRadius: '8px', boxShadow: 'var(--card-shadow)' }}>
          <Table>
            <thead>
              <tr>
                <th>Image Crop</th>
                <th>Predicted</th>
                <th>Similarity</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map(rev => (
                <tr key={rev.id}>
                  <td>
                    {rev.crop_url ? (
                      <img src={rev.crop_url} alt="Crop" style={{ height: '50px', width: '50px', objectFit: 'cover', borderRadius: '4px' }} />
                    ) : 'No Image'}
                  </td>
                  <td>{getProductName(rev.predicted_product_id)}</td>
                  <td>
                    {rev.predicted_similarity != null ? (
                      <Badge variant={rev.predicted_similarity > 0.5 ? 'success' : 'warning'}>
                        {rev.predicted_similarity.toFixed(2)}
                      </Badge>
                    ) : 'N/A'}
                  </td>
                  <td><Badge variant="warning">Pending</Badge></td>
                  <td>
                    <Button 
                      size="small" 
                      onClick={() => {
                        setSelectedReview(rev);
                        setResolutionType('existing');
                        setSelectedProductId('');
                        setSearchQuery('');
                        setResolveSuccess('');
                        setResolveError('');
                      }}
                    >
                      Review
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {selectedReview && (
        <Modal isOpen={!!selectedReview} onClose={() => !resolving && !resolveSuccess && setSelectedReview(null)}>
          <h3 style={{ marginTop: 0, marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
            Resolve Recognition
          </h3>
          
          {resolveSuccess ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
              <div style={{ fontSize: '4rem', color: 'var(--success-color)', marginBottom: '1rem' }}>✓</div>
              <h2 style={{ color: 'var(--success-color)' }}>{resolveSuccess}</h2>
              <p style={{ color: 'var(--text-light)' }}>Moving to next review...</p>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '2rem' }}>
              {/* Left Side: Details & Image */}
              <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ background: 'var(--background-color)', padding: '1rem', borderRadius: '8px', textAlign: 'center' }}>
                  {selectedReview.crop_url ? (
                    <img src={selectedReview.crop_url} alt="Shelf crop" style={{ maxWidth: '100%', maxHeight: '250px', borderRadius: '4px' }} />
                  ) : (
                    <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-light)' }}>No Image</div>
                  )}
                </div>
                
                <div style={{ background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div>
                      <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>Predicted Model</div>
                      <div style={{ fontWeight: '500' }}>{getProductName(selectedReview.predicted_product_id)}</div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-light)', fontSize: '0.85rem' }}>Similarity Score</div>
                      <div style={{ fontWeight: '500' }}>{selectedReview.predicted_similarity?.toFixed(2) || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Side: Resolution Form */}
              <div style={{ flex: '1', display: 'flex', flexDirection: 'column' }}>
                <ErrorMessage message={resolveError} />
                
                <form onSubmit={handleResolve} style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="resType"
                        checked={resolutionType === 'existing'}
                        onChange={() => setResolutionType('existing')}
                      />
                      Existing Product
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input 
                        type="radio" 
                        name="resType"
                        checked={resolutionType === 'new'}
                        onChange={() => setResolutionType('new')}
                      />
                      Others / New Product
                    </label>
                  </div>

                  {resolutionType === 'existing' ? (
                    <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <Input 
                        placeholder="Search Product..." 
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                      />
                      <div style={{ flex: '1', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '4px', maxHeight: '200px' }}>
                        {filteredProducts.map(p => (
                          <div 
                            key={p.id}
                            onClick={() => setSelectedProductId(p.id)}
                            style={{ 
                              padding: '0.75rem', 
                              cursor: 'pointer',
                              background: selectedProductId === p.id ? 'var(--primary-color)' : 'transparent',
                              color: selectedProductId === p.id ? '#fff' : 'inherit',
                              borderBottom: '1px solid var(--border-color)'
                            }}
                          >
                            <strong>{p.sku_code}</strong> — {p.name}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Product Name</label>
                        <Input value={newProductName} onChange={e => setNewProductName(e.target.value)} required />
                      </div>
                      <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Brand</label>
                        <Input value={newProductBrand} onChange={e => setNewProductBrand(e.target.value)} />
                      </div>
                      <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Category</label>
                        <Input value={newProductCategory} onChange={e => setNewProductCategory(e.target.value)} />
                      </div>
                    </div>
                  )}

                  <div style={{ marginTop: 'auto', paddingTop: '2rem', display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                    <Button type="button" variant="secondary" onClick={() => setSelectedReview(null)} disabled={resolving}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={resolving}>
                      {resolving ? 'Resolving...' : 'Resolve Review'}
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
};

export default Reviews;
