import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

export const startResearch = (company) =>
  API.post('/api/research', { company_name: company }).then(r => r.data);

export const getStatus = (sessionId) =>
  API.get(`/api/research/${sessionId}/status`).then(r => r.data);

export const getReport = (sessionId) =>
  API.get(`/api/research/${sessionId}/report`).then(r => r.data);

export const listSessions = () =>
  API.get('/api/sessions').then(r => r.data);

export const sendChat = (sessionId, message) =>
  API.post('/api/chat', { session_id: sessionId, message }).then(r => r.data);

export const getLLMStatus = () =>
  API.get('/api/llm/status').then(r => r.data);

export const getPDFUrl = (sessionId) =>
  `${API.defaults.baseURL}/api/research/${sessionId}/pdf`;

export default API;

export const getChromaStatus = () =>
  API.get('/api/chroma/status').then(r => r.data);

export const getMCPTools = () =>
  API.get('/api/mcp/tools').then(r => r.data);

export const getGraphSchema = () =>
  API.get('/api/graph/schema').then(r => r.data);
