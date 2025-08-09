# SocialApp - Production-like Backend (FastAPI)

This repository is a comprehensive example backend for a scalable social media platform,
built with FastAPI and async tooling. It includes many production-ready patterns and modules:
- Auth (JWT + OAuth placeholder flows), social logins skeleton
- User profiles, avatar upload via S3 presigned URLs
- Friend requests, blocking
- Posts, likes, comments with threading (nested comments)
- Real-time chat using WebSockets, horizontally scalable via Redis pub/sub
- Kafka producers and consumers for event-driven parts (messages, notifications, feed)
- MongoDB for message storage, PostgreSQL for relational data
- Redis caching with write-through and invalidation strategies
- Alembic migrations (initial migration included)
- Docker Compose for local development (Postgres, Mongo, Redis, Kafka, Zookeeper, Prometheus, Grafana)
- Prometheus metrics and logging
- CI via GitHub Actions (basic)
- Tests with pytest-asyncio

> ⚠️ This project is a complete scaffold but not a turnkey production deploy. Secrets (JWT secret, AWS keys)
> are placeholders and must be replaced. For production: use Kubernetes, managed DB, SSL, secrets manager, and hardened configs.

## Quick start (dev)
1. Install Docker & Docker Compose.
2. cp .env.example .env and fill required values.
3. docker-compose up --build
4. Apply migrations inside app container: `alembic upgrade head`
5. Visit http://localhost:8000/docs for OpenAPI UI
