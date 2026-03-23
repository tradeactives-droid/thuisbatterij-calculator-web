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
- **Zwarte achtergrond transparant maken** (effen zwart rond het logo):
  - `python scripts/make_logo_transparent.py --black-bg`
  - Optioneel drempel fijner afstellen: `--max-rgb 48` (lager = strenger, minder grijze rand).
- **Oudere pipeline** (schaakbord / wit): `python scripts/make_logo_transparent.py` gebruikt `logo-source.png`.
