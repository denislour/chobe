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

  it('reads private privacy and history endpoints', () => {
    api.privacy().subscribe();
    api.history().subscribe();
    http.expectOne('/api/v1/me/privacy-settings/').flush(privacyFixture);
    http.expectOne('/api/v1/me/viewing-history/').flush([]);
  });

  it('sends versioned privacy, history clear, and data export requests', () => {
    const values = { share_phone: false, record_history: false, version: 1 };
    api.savePrivacy(values).subscribe();
    api.clearHistory().subscribe();
    api.createAccountDataExport().subscribe();
    const privacy = http.expectOne('/api/v1/me/privacy-settings/');
    expect(privacy.request.method).toBe('PATCH');
    expect(privacy.request.body).toEqual(values);
    privacy.flush({ ...privacyFixture, ...values });
    const history = http.expectOne('/api/v1/me/viewing-history/');
    expect(history.request.method).toBe('DELETE');
    history.flush(null, { status: 204, statusText: 'No Content' });
    const exportRequest = http.expectOne('/api/v1/me/data-exports/');
    expect(exportRequest.request.method).toBe('POST');
    exportRequest.flush(
      { job_id: 'job', status: 'queued' },
      { status: 202, statusText: 'Accepted' },
    );
  });

  it('posts deletion credentials and reads a URL-encoded receipt separately', () => {
    const values = { password: 'current-password', confirmation: 'DELETE' };
    api.deleteAccount(values).subscribe();
    const request = http.expectOne('/api/v1/me/deletion-requests/');
    expect(request.request.body).toEqual(values);
    request.flush(
      { job_id: 'job', status: 'requested', receipt: 'receipt:token' },
      { status: 202, statusText: 'Accepted' },
    );
    api.deletionStatus('receipt:token').subscribe();
    const status = http.expectOne('/api/v1/account-deletion-status/receipt%3Atoken/');
    expect(status.request.method).toBe('GET');
    status.flush({ job_id: 'job', status: 'completed' });
  });
});
