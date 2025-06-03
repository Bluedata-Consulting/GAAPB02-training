import apiClient from '../config/api';

export const ticketService = {
  // Submit a new ticket
  submitTicket: async (ticketData) => {
    try {
      const response = await apiClient.post('/api/v1/tickets/submit', ticketData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Failed to submit ticket');
    }
  },

  // Health check
  checkHealth: async () => {
    try {
      const response = await apiClient