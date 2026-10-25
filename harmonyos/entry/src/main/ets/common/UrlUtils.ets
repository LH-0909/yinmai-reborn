export function normalizeBaseUrl(input: string): string {
  let value: string = input.trim();
  const schemeIndex: number = value.indexOf('://');
  const minimumLength: number = schemeIndex >= 0 ? schemeIndex + 3 : 1;
  while (value.endsWith('/') && value.length > minimumLength) {
    value = value.substring(0, value.length - 1);
  }
  return value;
}

export function isValidHttpUrl(input: string): boolean {
  const value: string = input.trim();
  const lower: string = value.toLowerCase();
  if (!lower.startsWith('http://') && !lower.startsWith('https://')) {
    return false;
  }
  if (value.indexOf(' ') >= 0 || value.indexOf('\t') >= 0 ||
    value.indexOf('\r') >= 0 || value.indexOf('\n') >= 0) {
    return false;
  }
  const schemeIndex: number = value.indexOf('://');
  const afterScheme: string = value.substring(schemeIndex + 3);
  if (afterScheme.length === 0) {
    return false;
  }
  let authorityEnd: number = afterScheme.length;
  const slash: number = afterScheme.indexOf('/');
  const query: number = afterScheme.indexOf('?');
  const fragment: number = afterScheme.indexOf('#');
  if (slash >= 0 && slash < authorityEnd) {
    authorityEnd = slash;
  }
  if (query >= 0 && query < authorityEnd) {
    authorityEnd = query;
  }
  if (fragment >= 0 && fragment < authorityEnd) {
    authorityEnd = fragment;
  }
  const authority: string = afterScheme.substring(0, authorityEnd);
  if (authority.length === 0 || authority.indexOf('@') >= 0) {
    return false;
  }
  return true;
}

export function joinApiPath(baseUrl: string, suffix: string): string {
  const base: string = normalizeBaseUrl(baseUrl);
  const path: string = suffix.startsWith('/') ? suffix : '/' + suffix;
  return base + path;
}

export function resolveBackendUrl(apiBaseUrl: string, rawUrl: string): string {
  const raw: string = rawUrl.trim();
  if (raw.length === 0) {
    return '';
  }
  const lower: string = raw.toLowerCase();
  if (lower.startsWith('http://') || lower.startsWith('https://')) {
    return raw;
  }
  if (raw.indexOf('://') >= 0) {
    return '';
  }
  const base: string = normalizeBaseUrl(apiBaseUrl);
  if (base.length === 0) {
    return '';
  }
  return raw.startsWith('/') ? base + raw : base + '/' + raw;
}
