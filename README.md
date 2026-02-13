# Quick Start Guide

## Backend Setup

### 1. Start the Backend Server

```bash
cd backend
python main.py
```

Expected output:
```
Creating database tables...
Database tables created successfully!
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Test Health Endpoint

Open browser or use curl:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "db": "connected",
  "gpu": true,
  "gpu_count": 1,
  "gpu_name": "NVIDIA GeForce GTX 1660 SUPER"
}
```

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

Expected output:
```
VITE v5.0.8  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 3. Open in Browser

Navigate to `http://localhost:5173` and click "Check System Health" button.

## Database Verification

### Check Tables in PostgreSQL

```bash
psql -U postgres -d interview_db -c "\dt"
```

Expected tables:
- users
- job_postings
- interview_sessions
- transcripts
- evaluation_reports
- question_bank

## Troubleshooting

### Backend Issues

**Problem**: `POSTGRES_CONNECTION_STRING not found`
- **Solution**: Ensure `.env` file exists in `/backend` directory

**Problem**: Database connection error
- **Solution**: Verify PostgreSQL is running and credentials in `.env` are correct

### Frontend Issues

**Problem**: CORS error
- **Solution**: Ensure backend is running on port 8000 and frontend on port 5173

**Problem**: `npm install` fails
- **Solution**: Ensure Node.js version is 18+ (`node --version`)
