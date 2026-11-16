import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// ตอน dev ส่ง /api ไปที่ FastAPI ที่รันบนเครื่อง (เลียนแบบ ALB ที่แยก path /api/*)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  // Only the frontend tests (the Python backend in backend/ has its own pytest suite).
  test: { include: ['tests/**/*.test.js'] },
});
