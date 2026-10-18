import { HttpErrorResponse } from '@angular/common/http';
export function listingError(error: HttpErrorResponse): string {
  const messages: Record<number, string> = {
    403: 'You do not have access, or your security check expired. Reload and sign in again.',
    404: 'This item is no longer available.',
    409: 'This version changed. Reload the latest values and review your changes.',
    429: 'Too many requests. Please wait before trying again.',
  };
  if (messages[error.status]) return messages[error.status];
  if (error.status === 400) {
    const values = error.error;
    if (typeof values === 'string') return values;
    if (values?.detail) return String(values.detail);
    return (
      Object.entries(values ?? {})
        .map(
          ([key, value]) =>
            `${key}: ${typeof value === 'object' && !Array.isArray(value) ? JSON.stringify(value) : String(value)}`,
        )
        .join(' · ') || 'Check your entries and try again.'
    );
  }
  return 'Unable to complete this request. Please try again.';
}
