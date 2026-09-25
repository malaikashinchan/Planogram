import api from '../api/api';

const planogramService = {
  getPlanograms: async (storeId = null, skip = 0, limit = 100) => {
    let url = `/planograms/?skip=${skip}&limit=${limit}`;
    if (storeId) url += `&store_id=${storeId}`;
    const response = await api.get(url);
    return response.data;
  },

  getPlanogram: async (id) => {
    const response = await api.get(`/planograms/${id}`);
    return response.data;
  },

  uploadPlanogram: async (name, storeId, file) => {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('store_id', storeId);
    formData.append('file', file);

    const response = await api.post('/planograms/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  deletePlanogram: async (id) => {
    const response = await api.delete(`/planograms/${id}`);
    return response.data;
  }
};

export default planogramService;
