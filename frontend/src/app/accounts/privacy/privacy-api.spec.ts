import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { PrivacyApi } from './privacy-api';
import { privacyFixture } from '@app/accounts/account-fixtures';

describe('PrivacyApi', () => {
  let api: PrivacyApi;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(PrivacyApi);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => {
    document.cookie = 'XSRF-TOKEN=; Max-Age=0; path=/';
    http.verify();
  });

  it('reads private privacy settings', () => {
    api.privacy().subscribe();
    http.expectOne('/api/v1/me/privacy-settings/').flush(privacyFixture);
  });

  it('sends versioned privacy settings', () => {
    const values = { share_phone: false, record_history: false, version: 1 };
    api.savePrivacy(values).subscribe();
    const privacy = http.expectOne('/api/v1/me/privacy-settings/');
    expect(privacy.request.method).toBe('PATCH');
    expect(privacy.request.body).toEqual(values);
    privacy.flush({ ...privacyFixture, ...values });
  });

});
