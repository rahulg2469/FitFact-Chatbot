# FitFact Deployment Guide

Deploy FitFact to Vercel with Firebase for authentication and database.

## Prerequisites

- Node.js 18+
- Vercel account (free tier works)
- Firebase account (free tier works)
- Anthropic API key

---

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **Add Project** → Name it "fitfact" → Create
3. Enable services:

### Authentication
1. Click **Authentication** → Get Started
2. Go to **Sign-in method** tab
3. Enable **Email/Password**
4. Enable **Google** (add your email as support email)

### Firestore Database
1. Click **Firestore Database** → Create database
2. Select **Start in production mode**
3. Choose closest region (us-central1)
4. Click **Enable**

### Firestore Rules
Go to **Rules** tab and paste:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      
      // Conversations subcollection
      match /conversations/{convoId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
      
      // Query history subcollection
      match /queryHistory/{queryId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
    
    // Cache is readable by all authenticated users, writable by functions
    match /cache/{queryHash} {
      allow read: if request.auth != null;
      allow write: if false; // Only via server
    }
    
    // Papers collection - read only for users
    match /papers/{pmid} {
      allow read: if request.auth != null;
      allow write: if false; // Only via server
    }
  }
}
```

Click **Publish**.

### Get Firebase Config
1. Go to **Project Settings** (gear icon)
2. Scroll to **Your apps** → Click web icon (</>) 
3. Register app (name: "FitFact Web")
4. Copy the config object:

```javascript
const firebaseConfig = {
  apiKey: "AIza...",
  authDomain: "fitfact-xxxxx.firebaseapp.com",
  projectId: "fitfact-xxxxx",
  storageBucket: "fitfact-xxxxx.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};
```

---

## Step 2: Configure Environment Variables

Create `.env.local` in `web/frontend/`:

```bash
cd web/frontend
cp .env.example .env.local
```

Fill in the values from Firebase config:

```
VITE_FIREBASE_API_KEY=AIza...
VITE_FIREBASE_AUTH_DOMAIN=fitfact-xxxxx.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=fitfact-xxxxx
VITE_FIREBASE_STORAGE_BUCKET=fitfact-xxxxx.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Step 3: Test Locally

```bash
cd web/frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:5173 and test:
- Create account with email/password
- Sign in with Google
- Send a chat message

---

## Step 4: Deploy to Vercel

### Option A: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy from frontend directory
cd web/frontend
vercel

# Follow prompts:
# - Set up and deploy? Y
# - Which scope? (your account)
# - Link to existing project? N
# - Project name: fitfact
# - Directory: ./
# - Override settings? N
```

### Option B: GitHub Integration

1. Push code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click **Add New** → **Project**
4. Import your GitHub repo
5. Set **Root Directory** to `web/frontend`
6. Click **Deploy**

### Add Environment Variables

In Vercel dashboard:
1. Go to **Settings** → **Environment Variables**
2. Add each variable:

| Name | Value |
|------|-------|
| `VITE_FIREBASE_API_KEY` | AIza... |
| `VITE_FIREBASE_AUTH_DOMAIN` | fitfact-xxx.firebaseapp.com |
| `VITE_FIREBASE_PROJECT_ID` | fitfact-xxx |
| `VITE_FIREBASE_STORAGE_BUCKET` | fitfact-xxx.appspot.com |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | 123456789 |
| `VITE_FIREBASE_APP_ID` | 1:123... |
| `ANTHROPIC_API_KEY` | sk-ant-... |

3. Click **Redeploy** to apply changes

---

## Step 5: Configure Firebase Auth Domains

1. In Firebase Console → **Authentication** → **Settings**
2. Go to **Authorized domains**
3. Add your Vercel domain: `fitfact.vercel.app` (or custom domain)

---

## Step 6: Test Production

Visit your Vercel URL and test all features:
- ✅ Email signup with verification
- ✅ Google sign-in
- ✅ Chat with AI responses
- ✅ Conversation history persistence
- ✅ Sign out

---

## Troubleshooting

### "Firebase: Error (auth/unauthorized-domain)"
- Add your domain to Firebase Auth authorized domains

### API calls failing
- Check Vercel environment variables are set correctly
- Verify ANTHROPIC_API_KEY is valid

### Firestore permission denied
- Check Firestore rules are published
- Ensure user is authenticated before accessing data

### Google sign-in not working
- Enable Google provider in Firebase Auth
- Add authorized domains in Firebase

---

## Custom Domain (Optional)

1. In Vercel dashboard → **Settings** → **Domains**
2. Add your custom domain
3. Configure DNS as instructed
4. Add domain to Firebase authorized domains

---

## Cost Estimates (Free Tier)

| Service | Free Tier | Typical Usage |
|---------|-----------|---------------|
| Vercel | 100GB bandwidth/month | ✅ Plenty |
| Firebase Auth | 10K verifications/month | ✅ Plenty |
| Firestore | 1GB storage, 50K reads/day | ✅ Plenty |
| Anthropic | Pay per token | ~$0.01/query |

For a small project, you'll likely stay within free tiers except for Anthropic API costs.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                      Vercel                              │
│  ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │  React Frontend │───▶│  Serverless API Functions   │ │
│  │  (Static Build) │    │  /api/chat.py               │ │
│  └────────┬────────┘    └──────────────┬──────────────┘ │
│           │                            │                 │
└───────────┼────────────────────────────┼─────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────┐    ┌─────────────────────────┐
│     Firebase          │    │     External APIs       │
│  • Auth               │    │  • Anthropic Claude     │
│  • Firestore DB       │    │  • PubMed               │
└───────────────────────┘    └─────────────────────────┘
```
