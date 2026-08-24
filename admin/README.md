# Yard moderation console

This deliberately small Next.js application consumes Yard's moderator-only APIs. In local
development, use the development moderator identity. That authentication route returns 404 outside
the backend's development environment; production access uses the normal authenticated Yard account
with `is_admin` granted through an operational database process.

```bash
npm install
npm run dev
```

Set `NEXT_PUBLIC_YARD_API_URL` when the API is not at `http://localhost:8000/api/v1`.
