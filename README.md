# LLM Chat Application

Samsonov Vladimir N4150c

## Project Overview
This project implements a local LLM-powered chat application with user authentication, persistent conversation history, and a single-page application (SPA) frontend. The backend is built with FastAPI, uses PostgreSQL as the primary relational database, and leverages Redis for session management and refresh token storage.

## Prerequisites
- Python 3.10 or higher
- Docker Desktop and Docker Compose
- `pip` package manager

## Installation and Setup

### 1. Environment Preparation
Create and activate a virtual environment, then install dependencies:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
```powershell
copy .env.example .env
```

### 3. Database and Redis Initialization
```powershell
docker compose up -d
alembic upgrade head
```

## Running the Application
```powershell
uvicorn app.main:app --reload
python -m http.server 5173 -d frontend
```
Access the application at http://localhost:5173

## Architecture

### Frontend Mode and Structural Pattern

The application utilizes a Single-Page Application (SPA) frontend served statically. The backend strictly adheres to the Model–Controller–Service (MCS) pattern:
- Models (app/models/): SQLAlchemy ORM definitions representing database tables (User, Chat, Message). Handle data persistence and relational mappings.
- Controllers (app/routers/): FastAPI route handlers responsible for HTTP request parsing, input validation, and response serialization. Controllers contain no business logic and delegate all operational tasks to the service layer.
- Services (app/services/): Dedicated modules containing business logic, transaction management, LLM inference orchestration, and external API communication (GitHub OAuth, Redis interactions).
This separation ensures clear responsibility boundaries, simplifies unit testing, and maintains thin, declarative API endpoints.

### Authentication and Session Management

The authentication system implements a stateless JWT access token flow combined with server-side refresh token management via Redis:
1. Token Issuance: Upon successful credential validation (password or GitHub OAuth), the server generates:
    - An Access Token (JWT): Short-lived, cryptographically signed, and transmitted in the Authorization: Bearer <token> header. Validated statelessly by the backend middleware.
    - A Refresh Token (JWT/Opaque): Long-lived, stored exclusively in Redis under the key refresh_token:{token}. The value contains the associated user ID.
2. Redis Interaction: Refresh tokens are persisted in Redis with a strict TTL of 30 days. Redis serves as a centralized, fast-access session store.
3. Token Refresh Flow: When an access token expires, the client submits the refresh token to /api/auth/refresh. The backend:
    - Queries Redis for the key refresh_token:{token}.
    - Validates the associated user exists in PostgreSQL.
    - Deletes the old refresh token from Redis (rotation).
    - Issues a new access/refresh token pair.
    - Stores the new refresh token in Redis with a reset TTL.
4. Security Properties: All refresh operations are atomic. Compromised or used refresh tokens are immediately invalidated by deletion from Redis. Passwords are hashed using bcrypt prior to database persistence.
