# microapp-kit

Kit keamanan untuk layanan di ekosistem My-SUKA. Lihat `../docs/KEAMANAN-MICROAPP.md`.

- `python/mysuka_sso.py`, `python/example_fastapi.py` — verifier, exchange, PKCE, back-channel logout, cookie, header.
- `node/mysuka-sso.mjs` — padanan Node (butuh `jose`).
- `conformance/check-service.mjs` — pemeriksa black-box untuk satu layanan (jalankan hanya pada layanan yang Anda miliki).

Uji: `npm run kit:test` (Node + pemeriksa) dan `cd portal-api && python -m pytest` (kit Python, termasuk alur penuh terhadap portal-api nyata).
