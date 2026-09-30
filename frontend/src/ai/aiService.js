import api from '../api/api';

export const aiService = {
  chat: async (payload) => {
    try {
      const response = await api.post('/ai/chat', payload);
      return response.data;
    } catch (error) {
      console.error("Error in AI chat service:", error);
      throw error;
    }
  }
};
