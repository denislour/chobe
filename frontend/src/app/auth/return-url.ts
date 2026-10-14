export function safeReturnUrl(value: string | null): string | null {
  if (!value?.startsWith('/') || value.startsWith('//')) return null;
  try {
    const decoded = decodeURIComponent(value);
    if (decoded.startsWith('//') || decoded.includes('\\')) return null;
    if (
      [...decoded].some(
        (character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127,
      )
    )
      return null;
    const url = new URL(value, 'https://chobe.invalid');
    if (url.origin !== 'https://chobe.invalid') return null;
    if (
      /^\/(login|register|forgot-password|reset-password)(\/|$)/.test(
        decodeURIComponent(url.pathname),
      )
    )
      return null;
    return url.pathname + url.search + url.hash;
  } catch {
    return null;
  }
}
