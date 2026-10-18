import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter(routes), provideHttpClient(), provideHttpClientTesting()],
    }),
  );

  it('creates the app', () => {
    expect(TestBed.createComponent(App).componentInstance).toBeTruthy();
  });

  it('opens discovery at the root route', async () => {
    const fixture = TestBed.createComponent(App);
    await TestBed.inject(Router).navigateByUrl('/');
    await fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe('/');
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/v1/home/').flush({ categories: [], latest: [] });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('h1')?.textContent).toBe(
      'Good things deserve another home.',
    );
    http.verify();
  });
});
