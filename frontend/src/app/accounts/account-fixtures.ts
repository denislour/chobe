import { PrivacyData } from '@app/accounts/privacy/privacy-api';
import { ProfileData } from '@app/accounts/profile/profile-api';

export const profileFixture: ProfileData = {
  display_name: 'Member',
  username: 'member',
  email: 'member@example.com',
  area: 'Ha Noi',
  bio: '',
  phone: '',
  avatar_url: null,
  version: 1,
  updated_at: '2026-10-13T00:00:00Z',
};

export const privacyFixture: PrivacyData = {
  share_phone: false,
  record_history: true,
  consent_at: null,
  version: 1,
  updated_at: '2026-10-13T00:00:00Z',
};
