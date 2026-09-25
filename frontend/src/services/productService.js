import api from '../api/api';

const productService = {
  getProducts: async (skip = 0, limit = 100) => {
    const response = await api.get(`/products/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getProduct: async (id) => {
    const response = await api.get(`/products/${id}`);
    return response.data;
  },

  createProduct: async (productData) => {
    const response = await api.post('/products/', productData);
    return response.data;
  },

  uploadProductCatalogue: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/products/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  previewProductCatalogue: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/products/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  }
};

export default productService;
