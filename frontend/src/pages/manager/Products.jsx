import React, { useState, useEffect, useRef } from 'react';
import productService from '../../services/productService';
import Table from '../../components/Table/Table';
import Input from '../../components/Input/Input';
import Button from '../../components/Button/Button';
import Modal from '../../components/Modal/Modal';
import Spinner from '../../components/Spinner/Spinner';
import ErrorMessage from '../../components/ErrorMessage/ErrorMessage';
import EmptyState from '../../components/EmptyState/EmptyState';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Add Product Modal State
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [addForm, setAddForm] = useState({ sku_code: '', name: '', brand: '', category: '' });
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState('');

  // Import Modal State
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [parsedPreview, setParsedPreview] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');
  const [importSuccess, setImportSuccess] = useState('');
  const fileInputRef = useRef(null);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const data = await productService.getProducts(0, 100);
      setProducts(data);
      setFilteredProducts(data);
    } catch (err) {
      setError('Failed to load products.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    const lower = searchTerm.toLowerCase();
    const filtered = products.filter(p => 
      p.sku_code.toLowerCase().includes(lower) || 
      p.name.toLowerCase().includes(lower) ||
      (p.brand && p.brand.toLowerCase().includes(lower)) ||
      (p.category && p.category.toLowerCase().includes(lower))
    );
    setFilteredProducts(filtered);
  }, [searchTerm, products]);

  // Handle single product add
  const handleAddSubmit = async (e) => {
    e.preventDefault();
    setAdding(true);
    setAddError('');
    try {
      await productService.createProduct(addForm);
      setIsAddOpen(false);
      setAddForm({ sku_code: '', name: '', brand: '', category: '' });
      await fetchProducts();
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to create product.');
    } finally {
      setAdding(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    setImportFile(file);
    setImportError('');
    setParsedPreview(null);

    if (file) {
      try {
        const result = await productService.previewProductCatalogue(file);
        setParsedPreview(result);
      } catch (err) {
        setImportError(err.response?.data?.detail || "Preview failed.");
        setImportFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    }
  };

  const handleImportSubmit = async () => {
    if (!importFile) return;
    setImporting(true);
    setImportError('');
    
    try {
      const res = await productService.uploadProductCatalogue(importFile);
      setImportSuccess(`Import successful! Created: ${res.created}, Updated: ${res.updated}`);
      await fetchProducts();
      setTimeout(() => {
        setIsImportOpen(false);
        setImportSuccess('');
        setImportFile(null);
        setParsedPreview(null);
      }, 2000);
    } catch (err) {
      setImportError(err.response?.data?.detail || 'Import failed.');
    } finally {
      setImporting(false);
    }
  };

  if (loading && products.length === 0) return <Spinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h2>Product Master</h2>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ width: '250px' }}>
            <Input 
              placeholder="Search products..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Button variant="secondary" onClick={() => setIsImportOpen(true)}>Import Products</Button>
          <Button onClick={() => setIsAddOpen(true)}>+ Add Product</Button>
        </div>
      </div>
      
      {products.length === 0 ? (
        <div style={{ textAlign: 'center', background: 'var(--surface-color)', padding: '4rem 2rem', borderRadius: '8px', boxShadow: 'var(--card-shadow)' }}>
          <h3 style={{ marginBottom: '1rem', color: 'var(--text-color)' }}>Product Master is empty</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', maxWidth: '400px', margin: '0 auto 2rem' }}>
            Import your product catalogue or add a product manually to get started before uploading planograms.
          </p>
          <Button onClick={() => setIsImportOpen(true)} size="large">Import Products</Button>
        </div>
      ) : filteredProducts.length === 0 ? (
        <EmptyState message="No products found matching your search." />
      ) : (
        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <Table>
            <thead>
              <tr>
                <th>SKU Code</th>
                <th>Name</th>
                <th>Brand</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map(product => (
                <tr key={product.id}>
                  <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{product.sku_code}</td>
                  <td>{product.name}</td>
                  <td>{product.brand || '-'}</td>
                  <td>{product.category || '-'}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {/* Add Product Modal */}
      <Modal isOpen={isAddOpen} onClose={() => !adding && setIsAddOpen(false)}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Add Product</h3>
        <ErrorMessage message={addError} />
        <form onSubmit={handleAddSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>SKU Code (Optional)</label>
            <Input 
              value={addForm.sku_code} 
              onChange={e => setAddForm({...addForm, sku_code: e.target.value})} 
              placeholder="Leave blank to auto-generate" 
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Product Name</label>
            <Input value={addForm.name} onChange={e => setAddForm({...addForm, name: e.target.value})} required />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Brand</label>
            <Input value={addForm.brand} onChange={e => setAddForm({...addForm, brand: e.target.value})} required />
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 500 }}>Category</label>
            <Input value={addForm.category} onChange={e => setAddForm({...addForm, category: e.target.value})} required />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
            <Button type="button" variant="secondary" onClick={() => setIsAddOpen(false)} disabled={adding}>Cancel</Button>
            <Button type="submit" disabled={adding}>{adding ? 'Saving...' : 'Save Product'}</Button>
          </div>
        </form>
      </Modal>

      {/* Import Products Modal */}
      <Modal isOpen={isImportOpen} onClose={() => !importing && setIsImportOpen(false)}>
        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Import Product Master</h3>
        
        {importSuccess ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--success-color)' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✓</div>
            <h3>{importSuccess}</h3>
          </div>
        ) : (
          <>
            <ErrorMessage message={importError} />
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ background: 'var(--primary-light)', padding: '1rem', borderRadius: '4px', marginBottom: '1rem', borderLeft: '4px solid var(--primary-color)' }}>
                <strong>Important:</strong> We map columns by their exact order, regardless of what the column is named.
                <br/>
                Your file <strong>must</strong> be in this exact sequence:
                <br/>
                <code>1. SKU ID | 2. Product Name | 3. Brand (Optional) | 4. Category (Optional)</code>
              </div>
              
              <div style={{ background: 'var(--background-color)', padding: '1rem', borderRadius: '4px', border: '1px dashed var(--border-color)', textAlign: 'center' }}>
                <input 
                  type="file" 
                  accept=".csv,.xls,.xlsx,.json"
                  onChange={handleFileChange}
                  ref={fileInputRef}
                  style={{ display: 'block', width: '100%', cursor: 'pointer' }}
                />
              </div>
            </div>

            {parsedPreview && (
              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 500 }}>Previewing {parsedPreview.preview.length} of {parsedPreview.totalRows} products</span>
                </div>
                <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '4px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead style={{ background: 'var(--background-color)', borderBottom: '1px solid var(--border-color)' }}>
                      <tr>
                        <th style={{ padding: '0.5rem', textAlign: 'left' }}>SKU</th>
                        <th style={{ padding: '0.5rem', textAlign: 'left' }}>Name</th>
                        <th style={{ padding: '0.5rem', textAlign: 'left' }}>Brand</th>
                        <th style={{ padding: '0.5rem', textAlign: 'left' }}>Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parsedPreview.preview.map((row, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '0.5rem' }}>{row.sku_code}</td>
                          <td style={{ padding: '0.5rem' }}>{row.name}</td>
                          <td style={{ padding: '0.5rem' }}>{row.brand}</td>
                          <td style={{ padding: '0.5rem' }}>{row.category}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <Button type="button" variant="secondary" onClick={() => {
                setIsImportOpen(false);
                setImportFile(null);
                setParsedPreview(null);
                setImportError('');
              }} disabled={importing}>
                Cancel
              </Button>
              <Button 
                onClick={handleImportSubmit} 
                disabled={!parsedPreview || importing}
              >
                {importing ? 'Importing...' : 'Confirm Import'}
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
};

export default Products;
