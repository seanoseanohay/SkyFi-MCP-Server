# Config directory

## credentials.json (optional)

For **local** use you can store your SkyFi API key and URLs in `config/credentials.json` instead of (or in addition to) `.env`. The server uses them when no request header and no env var is set.

1. Copy `credentials.json.example` to `credentials.json`.
2. Set `api_key`, and optionally `api_base_url`, `webhook_base_url`, `notification_url`.
3. Do not commit `credentials.json` (it is gitignored).

**Precedence:** Request header (`X-Skyfi-Api-Key`) → environment variables → `config/credentials.json`.

Override the path with the **`SKYFI_CREDENTIALS_PATH`** environment variable (e.g. to a file outside the repo).

See the main [README](../README.md) for full server setup.
