---
name: Never commit API keys or .env files
description: User explicitly asked to never commit the GROQ API key or .env files to git
type: feedback
---

Never stage or commit `.env` files or any file containing API keys (e.g. GROQ_API_KEY).

**Why:** User's GROQ API key is stored in `backend/app/.env` and must stay out of version control.

**How to apply:** Before any `git add` or commit, verify `.env` files are gitignored and not staged. Never suggest committing secrets.
