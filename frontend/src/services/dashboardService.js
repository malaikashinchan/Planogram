import api from '../api/api';

const dashboardService = {
  getAuditStatistics: async (days = 7) => {
    const response = await api.get(`/dashboard/audit-statistics?days=${days}`);
    return response.data;
  },

  getComplianceTrends: async (days = 30) => {
    const response = await api.get(`/dashboard/compliance-trends?days=${days}`);
    return response.data;
  },

  getModelStatus: async () => {
    const response = await api.get('/dashboard/model-status');
    return response.data;
  }
};

export default dashboardService;
