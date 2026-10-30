import { it, expect, vi, afterEach } from 'vitest';
vi.mock('../src/config', () => ({ config: { useMock: false } }));
vi.mock('../src/api/endpoints', () => ({ api: { getUploadUrl: vi.fn() } }));
import { api } from '../src/api/endpoints';
import { uploadImage } from '../src/utils/upload';
afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });
it('rejects unsupported MIME before requesting a URL', async () => {
  await expect(uploadImage({ type: 'image/svg+xml', size: 1 })).rejects.toThrow('Only PNG');
  expect(api.getUploadUrl).not.toHaveBeenCalled();
});
it('rejects oversize files', async () => { await expect(uploadImage({type:'image/png',size:5*1024*1024+1})).rejects.toThrow('5 MB'); });
it('requires both presign URLs in real mode', async () => { api.getUploadUrl.mockResolvedValue({upload_url:null,file_url:''}); await expect(uploadImage({type:'image/png',size:1,name:'x.png'})).rejects.toThrow('Invalid upload response'); });
it('PUTs the file without a Cognito authorization header', async () => {
  api.getUploadUrl.mockResolvedValue({upload_url:'https://upload.example.test/signed',file_url:'https://images.example.test/x.png'});
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(null,{status:200})));
  const file={type:'image/png',size:1,name:'x.png'};
  expect(await uploadImage(file)).toBe('https://images.example.test/x.png');
  expect(fetch).toHaveBeenCalledWith('https://upload.example.test/signed',{method:'PUT',headers:{'Content-Type':'image/png'},body:file});
});
it('reports S3 failure instead of saving a broken cover', async () => {
  api.getUploadUrl.mockResolvedValue({upload_url:'https://upload.example.test/signed',file_url:'https://images.example.test/x.png'});
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(null,{status:403})));
  await expect(uploadImage({type:'image/png',size:1,name:'x.png'})).rejects.toThrow('Upload to S3 failed');
});
