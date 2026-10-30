// อัปโหลดรูปไป S3 แบบ presigned URL:
// 1) ขอ URL ชั่วคราวจาก FastAPI  2) PUT ไฟล์ตรงไป S3  3) ส่ง file_url กลับไปบันทึกใน RDS
import { config } from '../config';
import { api } from '../api/endpoints';

const MAX = 5 * 1024 * 1024;
const TYPES = ['image/png', 'image/jpeg', 'image/webp'];

export async function uploadImage(file) {
  if (!TYPES.includes(file.type)) throw new Error('Only PNG, JPG or WebP images are allowed.');
  if (file.size > MAX) throw new Error('Image must be 5 MB or smaller.');
  const { upload_url, file_url } = await api.getUploadUrl(file.name, file.type);
  if (!config.useMock && (!upload_url || !file_url)) throw new Error('Invalid upload response: upload_url and file_url are required.');
  if (upload_url) {
    const res = await fetch(upload_url, { method: 'PUT', headers: { 'Content-Type': file.type }, body: file });
    if (!res.ok) throw new Error('Upload to S3 failed.');
  }
  return file_url;
}
