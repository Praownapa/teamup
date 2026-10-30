// รูปประกอบทั้งหมดของแอปรวมไว้ที่นี่
// - ภาพประกอบ: unDraw (see upstream license) แปลงเป็น SVG สีฟ้าของแอป เก็บไว้ใน public/illustrations
// - avatar: DiceBear "Notionists" โดย Zoish (CC0) สร้างจากชื่อผู้ใช้ ไม่ต้องโหลดรูปจากเน็ต

export const ill = (name) => `/illustrations/${name}.svg`;

// หมวดโปรเจกต์ -> ภาพปก + สีพื้นหลัง (ให้แต่ละการ์ดดูต่างกัน)
const CATEGORY = {
  'Course Project': { art: 'cat_course', bg: '#e0e7ff' },
  Competition: { art: 'cat_competition', bg: '#fef3c7' },
  'Senior Project': { art: 'cat_senior', bg: '#dcfce7' },
  'Startup Idea': { art: 'cat_startup', bg: '#fce7f3' },
  Research: { art: 'cat_research', bg: '#e0f2fe' },
};
export const categoryArt = (category) => CATEGORY[category] || { art: 'cat_default', bg: '#ede9fe' };

// avatar แบบภาพวาด สร้างจากชื่อ (ชื่อเดิมได้หน้าเดิมเสมอ)
// โหลดชุดภาพ avatar แยกไฟล์ (lazy) หน้าเว็บจะได้เปิดเร็ว แล้วค่อยแสดงภาพตามมา
const AV_BG = ['dbeafe', 'e0e7ff', 'fce7f3', 'dcfce7', 'fef3c7', 'e0f2fe', 'ede9fe', 'ffe4e6'];
const cache = new Map();
let gen = null;
export function loadAvatarGenerator() {
  gen ??= Promise.all([import('@dicebear/core'), import('@dicebear/notionists')])
    .then(([core, style]) => (name) => core.createAvatar(style, { seed: name, backgroundColor: AV_BG, radius: 50 }).toDataUri());
  return gen;
}
export const cachedAvatar = (name) => cache.get(name);
export async function avatarUri(name = '') {
  if (!cache.has(name)) cache.set(name, (await loadAvatarGenerator())(name));
  return cache.get(name);
}

