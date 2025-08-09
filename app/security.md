Security recommendations:
- Store secrets in a secrets manager (AWS Secrets Manager, HashiCorp Vault).
- Enable HTTPS (TLS) via ingress / load balancer. Use cert-manager in k8s.
- Use OAuth libraries (Authlib) for social logins; never implement raw OAuth flows.
- Rate limiting: put an API gateway (Kong/Traefik/NGINX) in front with Redis-backed limiter.
- Brute-force protection: lock accounts after repeated failed logins; add CAPTCHA for web UI.
- Use least privilege IAM roles for S3 access; use presigned URLs for uploads.
