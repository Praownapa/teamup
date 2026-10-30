export function errorMessage(data, fallback = 'Request failed.') {
  if (typeof data?.message === 'string' && data.message.trim()) return data.message;
  if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail;
  if (Array.isArray(data?.detail)) {
    const messages = data.detail.flatMap((item) => typeof item?.msg === 'string'
      ? [`${Array.isArray(item.loc) ? item.loc.join('.') + ': ' : ''}${item.msg}`] : []);
    if (messages.length) return messages.join('; ');
  }
  return fallback || 'Request failed.';
}
