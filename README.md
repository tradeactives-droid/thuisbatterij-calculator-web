# thuisbatterij-calculator-web
Frontend voor de thuisbatterij besparingscalculator met CSV

## BatteryEngine API & sessie
- Elke call naar het backend (`/compute_v3_profile`, `/generate_advice`, enz.) gebruikt:
  - `Authorization: Bearer <Supabase access_token>`
  - `x-session-token` (UUID in `localStorage` key `session_token`)
  - `x-device-id` en `x-device-fingerprint` (SHA-256 van UA+taal+scherm+timezone)
- Na login: rijen in Supabase-tabel **`active_sessions`** met hetzelfde `user_id` worden verwijderd; daarna één nieuwe rij met `session_token`. Zorg voor RLS policies zodat de ingelogde user dit mag.
- Bij **401** met `{ "error_code": "SESSION_INVALID" }`: token wordt gewist, uitloggen, terug naar login.

## Header-logo (`logo-header.png`)
- **Huidige header:** officiële Eco Metric-asset (PNG ongewijzigd), bedoeld voor donkere header (`#0f172a`).
- **Oud/transparant pipeline:** optioneel nog `logo-source.png` + `python scripts/make_logo_transparent.py` als je weer een transparante variant wilt genereren.
