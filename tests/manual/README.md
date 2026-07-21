# Manual API Checks

These scripts are intentionally excluded from automated pytest collection because they call a configured external environment.

Run the token-access probe from `backend/` with:

```bash
python tests/manual/check_token_access.py
```
