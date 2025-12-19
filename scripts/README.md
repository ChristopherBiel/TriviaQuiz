## Operational scripts

### `ensure_admin.py`
Create or promote an admin user with verified/approved flags set to `True`. Useful for seeding a fresh environment or recovering access when no admin exists.

Prereqs:
- AWS credentials with write access to the users table (`USERS_TABLE` env, default `TriviaUsersDev`)
- Standard app env vars (`AWS_REGION`, `SECRET_KEY` optional for this script)

Usage:
```bash
python scripts/ensure_admin.py \
  --username admin \
  --email admin@example.com \
  --password "super-secret"
```

The script is idempotent: if the user exists, it updates role/verification/approval and password; otherwise it creates the account.
