# Production Readiness Plan (Step-by-step)

This plan turns the repo into a production-ready deployment with Kubernetes, Helm, CI/CD, and strong security/observability. We’ll execute it in small, reviewable steps.

## Phase 0 — Prerequisites
- Container registry: GitHub Container Registry or ECR.
- Domains/DNS: Route53 (or provider of choice).
- Secrets store: AWS Secrets Manager or SOPS + Git (sealed-secrets alternative).
- TLS: cert-manager (DNS-01 or HTTP-01 with your DNS provider/ingress).

## Phase 1 — App hardening & configs
- Define envs via ConfigMap + Secret; remove hard-coded dev defaults in runtime.
- Resource requests/limits per component; readiness/liveness probes.
- Externalize connection strings (Postgres/Mongo/Redis/Kafka) via env/secret refs.
- Use AWS IRSA for S3 access (no static keys in pods).

## Phase 2 — Kubernetes base (manifests)
- Namespace: `wyd` (or per-env: `wyd-dev`, `wyd-prod`).
- Secrets (created out-of-band):
  - jwt: JWT_SECRET (or JWKS in the future)
  - fcm: FCM_SERVER_KEY
  - db: DATABASE_URL
  - redis/mongo/kafka urls
- ConfigMap: non-secret env (AWS_S3_BUCKET, AWS_S3_REGION, feature flags, etc.).
- Deployment (app):
  - image: ghcr.io/<owner>/wyd-backend:<git-sha>
  - replicas: 3+ (HPA controls actual)
  - probes: GET /healthz (add endpoint if missing)
  - resources: requests { cpu: 100m, mem: 256Mi } limits { cpu: 1, mem: 1Gi }
  - SA annotated for IRSA if S3 access needed.
- Service: ClusterIP on 8000.
- Ingress: NGINX (or ALB). TLS via cert-manager `Issuer`/`ClusterIssuer`.
- HPA: target CPU 60% (and/or RPS/custom metrics later).
- PDB: minAvailable=1.
- NetworkPolicy: lock down to ingress/egress as needed.

## Phase 3 — Helm chart
- Structure:
  - charts/wyd-backend/{Chart.yaml, values.yaml, templates/...}
- values.yaml:
  - image.repo/tag, env, secretsRef, resources, hpa, ingress, service, podAnnotations.
- Templatize Deployment, Service, Ingress, HPA, ConfigMap, ServiceAccount/Role.

## Phase 4 — Terraform (AWS baseline)
- VPC + subnets + NAT.
- EKS cluster + node groups (or Fargate profile for select pods).
- IRSA roles for app to access S3 (s3:PutObject/GetObject in your bucket).
- RDS for Postgres (or use managed alternative you prefer).
- MSK/Confluent Cloud for Kafka; ElastiCache for Redis; DocumentDB/Atlas for Mongo.
- Route53 zone + records; ACM certs (if ALB Ingress).

## Phase 5 — CI/CD (GitHub Actions)
- Build & push image on main/PR: cache layers, tag with sha + `latest`.
- Lint/test gates; docker build; push to registry.
- Deploy job: helm upgrade --install to target cluster/namespace.
- Store secrets in GitHub Environments; OIDC to assume AWS role for kubectl/helm.

## Phase 6 — Observability
- kube-prometheus-stack (Prometheus, Alertmanager, Grafana).
- Logging: Loki + Promtail (or CloudWatch). Add structured logs.
- Tracing (optional): OpenTelemetry collector + Jaeger/Tempo.
- SLOs & alerts: latency, error rate, saturation; Kafka lag.

## Phase 7 — WebSocket horizontal scale
- Ingress annotations for WebSocket pass-through & sticky sessions (if needed).
- WS fanout: Redis pub/sub or Kafka topic routing; test with multiple replicas.
- WS manager abstraction to ensure node-local sessions sync via backend bus.

## Phase 8 — Security
- Secrets out of repo; use IRSA & KMS. Avoid static AWS keys in pods.
- Image scanning (Trivy), policy enforcement (OPA/Gatekeeper/Kyverno).
- NetworkPolicies, PodSecurity/PSA, minimal RBAC.
- Backups (RDS, Redis), disaster recovery docs and drills.

## Phase 9 — Runbooks & SRE
- On-call runbook: deploy/rollback, rotate secrets, scale, DB migrations.
- Synthetics and post-deploy smoke checks.

---

## Immediate Next Steps (proposed)
1) Create Helm chart skeleton with values for:
   - env/secret refs, probes, resources, HPA, ingress, annotations.
2) Add a basic health endpoint `/healthz` if missing and wire probes.
3) Provision cert-manager and a ClusterIssuer (staging first) in ops/k8s.
4) Add GitHub Actions: build, push, helm upgrade (with OIDC to AWS).
5) Terraform skeleton for EKS + IRSA (optional if cluster already exists).

We can start with step 1 (Helm skeleton) and iterate.
