import api from '../api/api';

const storeService = {

  getStores: async (skip = 0, limit = 100) => {
    const response = await api.get(
      `/stores/?skip=${skip}&limit=${limit}`
    );

    return response.data;
  },


  getStore: async (id) => {
    const response = await api.get(
      `/stores/${id}`
    );

    return response.data;
  },


  createStore: async (storeData) => {
    const response = await api.post(
      '/stores/',
      storeData
    );

    return response.data;
  },


  updateStore: async (id, storeData) => {
    const response = await api.patch(
      `/stores/${id}`,
      storeData
    );

    return response.data;
  },


  updateStoreStatus: async (id, status) => {
    const response = await api.patch(
      `/stores/${id}/status`,
      { status }
    );

    return response.data;
  },

  deleteStore: async (id) => {
    const response = await api.delete(
      `/stores/${id}`
    );
    return response.data;
  },

  reverseGeocode: async (latitude, longitude) => {
    const response = await api.post(
      '/stores/geocode/reverse',
      {
        latitude,
        longitude,
      }
    );

    return response.data;
  },

};

export default storeService;
