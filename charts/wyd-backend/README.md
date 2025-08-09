# wyd-backend Helm Chart

Quickstart:

- Set your image repo/tag in `values.yaml`.
- Set ingress host and TLS secret names.
- Ensure secrets (e.g., `wyd-secrets`) are created with keys used in `values.yaml`.

Install:

```bash
helm upgrade --install wyd-backend charts/wyd-backend \
  --namespace wyd --create-namespace \
  --values charts/wyd-backend/values.yaml
```

Health:
- Liveness/Readiness probe hits `/healthz` on port 8000.

Env:
- Non-secret env via `values.yaml.env`
- Secret env via `values.yaml.secretEnv` referencing existing Secret(s).
