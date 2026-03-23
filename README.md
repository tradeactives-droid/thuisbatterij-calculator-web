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
- Bron: `logo-source.png` (hoge resolutie, **geen** screenshot van de site).
- Transparante achtergrond: `python scripts/make_logo_transparent.py`  
  (1) flood vanaf de rand, (2) schaakbord met chroma-bescherming, (3) kleine afgesloten witte holtes in letters (o, e, …).
