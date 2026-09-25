import api from '../api/api';

const auditService = {
  getAudits: async (skip = 0, limit = 100) => {
    const response = await api.get(`/audits/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getAudit: async (id) => {
    const response = await api.get(`/audits/${id}`);
    return response.data;
  },

  createAudit: async (storeId, planogramId, file) => {
    const formData = new FormData();
    formData.append('store_id', storeId);
    formData.append('planogram_id', planogramId);
    formData.append('image', file);
    
    const response = await api.post('/audits/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getAuditReviews: async (auditId) => {
    const response = await api.get(`/audits/${auditId}/reviews`);
    return response.data;
  },

  getAuditViolations: async (auditId) => {
    const response = await api.get(`/audits/${auditId}/violations`);
    return response.data;
  }
};

export default auditService;
