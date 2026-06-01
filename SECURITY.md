# Security Policy

## Reporting a Vulnerability

We take security seriously. If you discover a security issue in this project,
please **do not open a public GitHub issue**. Instead, email a private report to:

📧 **oritdaki@gmail.com**

Please include, where possible:

- A description of the issue and where it lives in the code.
- Steps to reproduce (smallest repro you can manage).
- The impact you assessed.
- Any suggested mitigation.

We aim to acknowledge reports within **7 business days** and address verified
issues as soon as practical.

## Supported Versions

This is an early-stage product (v1.x). Only the `main` branch is actively maintained.
Older commits are not patched.

## Security Posture (snapshot)

The following protections are in place at the time of writing:

### API (`backend/`)

| Control | Implementation |
|---|---|
| Authentication | Supabase JWT on `POST /predict` and `POST /ask`, verified against `https://<project>.supabase.co/auth/v1/user`. |
| Rate limiting | `slowapi`, 30 requests/minute per IP on the protected endpoints. |
| CORS | Allow-list of `localhost` for dev + regex for `*.vercel.app` + opt-in `EXTRA_CORS_ORIGINS`. |
| Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security: max-age=31536000; includeSubDomains`. |
| Webhook integrity | Stripe webhooks HMAC-verified before any DB write. |
| Secrets handling | All keys via environment variables; never committed. |

### Data (`Supabase`)

| Control | Implementation |
|---|---|
| Row-Level Security | All user tables enforce per-organization isolation. |
| Auth | Supabase Auth (email + password, bcrypt-hashed server-side). |
| Encryption at rest | Provided by Supabase (Postgres on managed infra). |
| Encryption in transit | TLS for every connection. |

### Payments

Card data never touches our infrastructure — Stripe Checkout handles tokenization
and we receive only the resulting `customer_id` / `subscription_id`.

### Accessibility

The site complies with WCAG 2.0 AA / ת"י 5568 — see [`/accessibility`](frontend/app/accessibility/page.tsx).

## What This Project is NOT Designed For

- High-throughput public-facing API. The rate limits are conservative.
- Storing PII beyond authentication identifiers (email).
- Use in regulated healthcare / financial domains without additional review.

## Acknowledgements

Thank you for helping keep i24 Ratings Forecast safe.
