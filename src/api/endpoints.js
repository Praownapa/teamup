// สัญญา API ที่ต้องตกลงกับคนทำ FastAPI (ดูตารางใน README) ทุกหน้าเรียกผ่านไฟล์นี้เท่านั้น
import { config } from '../config';
import { request } from './client';
import * as mock from './mock';

const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v !== '' && v != null)).toString();

const real = {
  // ผู้ใช้
  getMe: () => request('/users/me'),
  updateMe: (data) => request('/users/me', { method: 'PUT', body: data }),
  getUser: (id) => request(`/users/${id}`),
  getCounts: () => request('/users/me/counts'),
  getDashboard: () => request('/users/me/dashboard'),
  // โปรเจกต์
  listProjects: (q = {}) => request(`/projects?${qs(q)}`),
  listFilterOptions: () => request('/projects/filters'),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (data) => request('/projects', { method: 'POST', body: data }),
  updateProject: (id, data) => request(`/projects/${id}`, { method: 'PATCH', body: data }),
  toggleSave: (id) => request(`/projects/${id}/save`, { method: 'POST' }),
  reportProject: (id, reason) => request(`/projects/${id}/reports`, { method: 'POST', body: { reason } }),
  requestToJoin: (id, data) => request(`/projects/${id}/requests`, { method: 'POST', body: data }),
  // ทีม
  getTeam: (id) => request(`/projects/${id}`),
  getRecommendedStudents: (projectId) => request(`/projects/${projectId}/recommendations`),
  inviteStudent: (projectId, userId, role) => request(`/projects/${projectId}/invitations`, { method: 'POST', body: { user_id: userId, role } }),
  changeMemberRole: (projectId, userId, role) => request(`/projects/${projectId}/members/${userId}`, { method: 'PATCH', body: { role } }),
  removeMember: (projectId, userId) => request(`/projects/${projectId}/members/${userId}`, { method: 'DELETE' }),
  leaveTeam: (projectId) => request(`/projects/${projectId}/members/me`, { method: 'DELETE' }),
  // คำขอ / คำเชิญ
  listRequests: () => request('/requests'),
  respondRequest: (id, accept) => request(`/requests/${id}`, { method: 'PATCH', body: { status: accept ? 'accepted' : 'rejected' } }),
  cancelRequest: (id) => request(`/requests/${id}`, { method: 'DELETE' }),
  // แจ้งเตือน
  listNotifications: () => request('/notifications'),
  markRead: (id) => request(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => request('/notifications/read-all', { method: 'POST' }),
  // อัปโหลดรูป (S3 presigned URL)
  getUploadUrl: (filename, contentType) => request('/uploads/presign', { method: 'POST', body: { filename, content_type: contentType } }),
  // admin
  adminOverview: (period) => request(`/admin/overview?period=${period}`),
  adminResolveReport: (id, action) => request(`/admin/reports/${id}`, { method: 'PATCH', body: { status: action } }),
  adminSetUserStatus: (id, status) => request(`/admin/users/${id}`, { method: 'PATCH', body: { status } }),
  adminAddCategory: (name) => request('/admin/categories', { method: 'POST', body: { name } }),
  adminDeleteCategory: (name) => request(`/admin/categories/${encodeURIComponent(name)}`, { method: 'DELETE' }),
};

export const api = config.useMock ? mock : real;
