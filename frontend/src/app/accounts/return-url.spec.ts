import { safeReturnUrl } from './return-url';

describe('safeReturnUrl', () => {
  it('preserves a local action including its query and fragment', () => {
    expect(safeReturnUrl('/saved?sort=new#item')).toBe('/saved?sort=new#item');
  });

  for (const value of [
    null,
    '',
    'https://attacker.example',
    '//attacker.example',
    '/%2f%2fattacker.example',
    '/\\attacker.example',
    '/%5cattacker.example',
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password/uid/token',
    '/foo/../login',
    '/%6cogin',
    '/%0aevil',
    '/%zz',
  ]) {
    it(`rejects an unsafe or recursive destination: ${value}`, () => {
      expect(safeReturnUrl(value)).toBeNull();
    });
  }
});
