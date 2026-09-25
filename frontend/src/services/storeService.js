import api from '../api/api';

const storeService = {
  getStores: async (skip = 0, limit = 100) => {
    const response = await api.get(`/stores/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getStore: async (id) => {
    const response = await api.get(`/stores/${id}`);
    return response.data;
  },

  createStore: async (storeData) => {
    const response = await api.post('/stores/', storeData);
    return response.data;
  },

  updateStoreStatus: async (id, status) => {
    const response = await api.patch(`/stores/${id}/status`, { status });
    return response.data;
  }
};

export default storeService;
