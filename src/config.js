import { resolveConfig } from './config-values';

export const config = resolveConfig(window.__CONFIG__ || {}, import.meta.env);
