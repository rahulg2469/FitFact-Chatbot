# FitFact Web Application

Modern React frontend + FastAPI backend for FitFact chatbot.

## Quick Start

### 1. Install Backend Dependencies

```bash
cd web/backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd web/frontend
npm install
```

### 3. Start Both Servers

**Terminal 1 - Backend (port 8000):**
```bash
cd web/backend
python main.py
```

**Terminal 2 - Frontend (port 3000):**
```bash
cd web/frontend
npm run dev
```

### 4. Open Browser

Go to http://localhost:3000

## Features

- 🔐 **Google Sign-In** - One-click authentication
- 💬 **Chat Interface** - Particle News-inspired design
- 📚 **Research-Backed** - PubMed citations in every response
- 💾 **History** - Save and revisit past conversations
- 📱 **Mobile-Friendly** - Responsive design with bottom navigation

## Architecture

```
web/
├── backend/
│   ├── main.py          # FastAPI server
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/  # Reusable UI components
    │   ├── contexts/    # React contexts (Auth)
    │   ├── pages/       # Route pages
    │   └── main.jsx     # App entry point
    ├── index.html
    └── package.json
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/google` | Google OAuth login |
| POST | `/api/auth/logout` | Logout |
| GET | `/api/auth/me` | Get current user |
| POST | `/api/chat` | Send chat message |
| GET | `/api/user/history` | Get chat history |
| POST | `/api/user/save/:id` | Save response |
| GET | `/api/user/preferences` | Get preferences |

## Environment Variables

The app uses the `.env` file from the project root:
- `GOOGLE_CLIENT_ID` - For Google Sign-In
- `DB_*` - PostgreSQL connection
- `JWT_SECRET_KEY` - Session tokens
