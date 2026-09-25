import api from '../api/api';

const reviewService = {
  getPendingReviews: async () => {
    const response = await api.get('/reviews/pending');
    return response.data;
  },

  resolveReview: async (reviewId, resolutionData) => {
    const response = await api.post(`/reviews/${reviewId}/resolve`, resolutionData);
    return response.data;
  }
};

export default reviewService;
