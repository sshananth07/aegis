# Deployment

The CD workflow publishes Docker images to GitHub Container Registry on every
push to `main` and on manual dispatch.

Published images:

- `ghcr.io/<owner>/<repo>-api`
- `ghcr.io/<owner>/<repo>-web`

Required GitHub secrets for the web image build:

```text
NEXT_PUBLIC_API_URL
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
```

Optional GitHub secrets for deploy hooks:

```text
API_DEPLOY_HOOK_URL
WEB_DEPLOY_HOOK_URL
```

Use deploy hooks when your host supports them, such as Render deploy hooks or a
small webhook endpoint on your own infrastructure. The API service also needs
runtime environment variables on the host:

```text
DATABASE_URL
SUPABASE_URL
SUPABASE_ANON_KEY
GEMINI_API_KEY
CORS_ORIGINS
OLLAMA_ENABLED=false
```

Set `CORS_ORIGINS` to the deployed frontend origin, for example:

```text
CORS_ORIGINS=https://app.example.com
```
