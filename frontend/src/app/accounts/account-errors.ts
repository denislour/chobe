import { HttpErrorResponse } from '@angular/common/http';
export type FieldErrors = Partial<Record<string, string[]>>;

export function accountError(
  error: HttpErrorResponse,
  limitMessage = 'Too many requests.',
): {
  error: string;
  fieldErrors: FieldErrors;
} {
  const fieldErrors: FieldErrors = error.status === 400 ? (error.error ?? {}) : {};
  const messages: Record<number, string> = {
    400:
      fieldErrors['non_field_errors']?.[0] ??
      Object.values(fieldErrors).flat()[0] ??
      'Please check your entries.',
    403: 'Your security check expired. Reload this page and log in again.',
    404: 'This request was not found or its receipt has expired.',
    409: 'Your settings changed. Please review and save again.',
    410: 'This export has expired. Request a new one.',
    429: `${limitMessage} Please try again later.`,
  };
  const retryAfter = Number(error.headers.get('Retry-After'));
  if (error.status === 429 && retryAfter > 0) {
    const minutes = Math.ceil(retryAfter / 60);
    messages[429] = `${limitMessage} Try again in ${minutes} minute${minutes === 1 ? '' : 's'}.`;
  }
  return { fieldErrors, error: messages[error.status] ?? 'Unable to connect. Please try again.' };
}
