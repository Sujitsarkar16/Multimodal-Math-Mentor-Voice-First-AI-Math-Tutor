# 🚀 Math Mentor Deployment Guide

Complete step-by-step guide to deploy Math Mentor to production using Vercel (Frontend) and Render (Backend).

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backend Deployment (Render)](#backend-deployment-render)
3. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Testing & Verification](#testing--verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- ✅ GitHub repository with your code
- ✅ [Render account](https://render.com) (free tier available)
- ✅ [Vercel account](https://vercel.com) (free tier available)
- ✅ Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))
- ✅ Git installed and repository pushed to GitHub

---

## 🖥️ Backend Deployment (Render)

### Step 1: Push Code to GitHub

```bash
# Ensure all changes are committed
cd e:\Challanges\AI_Planet\app
git add .
git commit -m "Add deployment configuration"
git push origin main
```

### Step 2: Create Render Web Service

1. **Go to [Render Dashboard](https://dashboard.render.com/)**

2. **Click "New +" → "Web Service"**

3. **Connect GitHub Repository**
   - Click "Connect account" if first time
   - Select your Math Mentor repository
   - Click "Connect"

4. **Configure Service Settings**
   - **Name**: `math-mentor-backend`
   - **Region**: Select closest to your users
   - **Branch**: `main`
   - **Root Directory**: `server`
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

5. **Select Instance Type**
   - Choose **"Free"** tier for testing
   - For production, consider **"Starter"** ($7/month)

### Step 3: Configure Environment Variables

In Render dashboard, add the following environment variables:

| Key | Value | Required |
|-----|-------|----------|
| `PYTHON_VERSION` | `3.11.0` | Yes |
| `ENVIRONMENT` | `production` | Yes |
| `GEMINI_API_KEY` | Your API key from Google AI Studio | Yes |
| `LOG_LEVEL` | `INFO` | Yes |
| `DEFAULT_LLM_MODEL` | `gemini-2.0-flash-exp` | Yes |
| `DEFAULT_TEMPERATURE` | `0.2` | No |
| `MAX_OUTPUT_TOKENS` | `2000` | No |
| `ENABLE_GUARDRAILS` | `true` | No |
| `MAX_RETRIES` | `3` | No |
| `USE_LANGCHAIN_REACT` | `true` | No |
| `OCR_CONFIDENCE_THRESHOLD` | `0.75` | No |
| `ASR_CONFIDENCE_THRESHOLD` | `0.75` | No |
| `VERIFIER_CONFIDENCE_THRESHOLD` | `0.75` | No |
| `PARSER_AMBIGUITY_THRESHOLD` | `1` | No |
| `EMBEDDING_MODEL` | `models/embedding-001` | No |
| `TOP_K_RESULTS` | `5` | No |
| `SIMILARITY_THRESHOLD` | `0.75` | No |
| `APP_NAME` | `Math_Mentor` | No |
| `APP_VERSION` | `2.0.0` | No |

**To add environment variables:**
1. Scroll to "Environment" section
2. Click "Add Environment Variable"
3. Enter `Key` and `Value`
4. Click "Add" (repeat for each variable)

### Step 4: Enable Auto-Deploy

1. Under "Settings" → "Build & Deploy"
2. Enable **"Auto-Deploy"** - this will redeploy on every git push to main

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for first deployment
3. Monitor logs in real-time on Render dashboard

### Step 6: Note Your Backend URL

Once deployed, your backend will be available at:
```
https://math-mentor-backend.onrender.com
```

**Save this URL** - you'll need it for frontend configuration.

### Step 7: Verify Backend Health

Test the health endpoint:
```bash
curl https://math-mentor-backend.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0"
}
```

---

## 🎨 Frontend Deployment (Vercel)

### Step 1: Install Vercel CLI (Optional)

```bash
npm install -g vercel
```

### Step 2: Update Environment Configuration

Create `.env.production` in `frontend/` directory:

```bash
cd frontend
echo VITE_API_URL=https://math-mentor-backend.onrender.com/api/v1 > .env.production
```

**Replace the URL above with your actual Render backend URL.**

### Step 3: Deploy via Vercel Dashboard

1. **Go to [Vercel Dashboard](https://vercel.com/dashboard)**

2. **Click "Add New..." → "Project"**

3. **Import Git Repository**
   - Click "Import" next to your Math Mentor repository
   - If not listed, click "Add GitHub Account" and authorize Vercel

4. **Configure Project**
   - **Project Name**: `math-mentor`
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `dist` (auto-detected)

5. **Add Environment Variables**
   - Click "Environment Variables"
   - Add variable:
     - **Name**: `VITE_API_URL`
     - **Value**: `https://math-mentor-backend.onrender.com/api/v1`
     - **Environment**: Select all (Production, Preview, Development)

6. **Deploy**
   - Click **"Deploy"**
   - Wait 2-3 minutes for build and deployment

### Step 4: Note Your Frontend URL

Once deployed, your app will be available at:
```
https://math-mentor.vercel.app
```

Or a custom domain like:
```
https://math-mentor-[random-id].vercel.app
```

### Step 5: Alternative - Deploy via CLI

```bash
# Navigate to frontend directory
cd frontend

# Login to Vercel
vercel login

# Deploy to production
vercel --prod

# Follow prompts:
# - Set up and deploy? Yes
# - Scope: Your account
# - Link to existing project? No
# - Project name: math-mentor
# - Directory: ./
# - Override settings? No
```

---

## 🔧 Post-Deployment Configuration

### Update Backend CORS (Optional - for specific origin)

If you want to restrict CORS to only your Vercel frontend:

1. **Add environment variable to Render:**
   - Key: `ALLOWED_ORIGINS`
   - Value: `https://math-mentor.vercel.app`

2. **Update `server/app/main.py`:**
   ```python
   import os
   
   # CORS configuration
   allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
   if settings.ENVIRONMENT != "production":
       allowed_origins = ["http://localhost:5173", "http://localhost:3000"]
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=allowed_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **Commit and push** - Render will auto-deploy

### Custom Domain (Optional)

#### Vercel Custom Domain
1. Go to Vercel project settings → "Domains"
2. Add your domain
3. Configure DNS as instructed

#### Render Custom Domain
1. Go to Render service settings → "Custom Domain"
2. Add your domain
3. Configure DNS as instructed

---

## ✅ Testing & Verification

### 1. Backend Health Check

```bash
curl https://math-mentor-backend.onrender.com/health
```

### 2. API Documentation

Visit:
```
https://math-mentor-backend.onrender.com/docs
```

### 3. Test Solve Endpoint

```bash
curl -X POST https://math-mentor-backend.onrender.com/api/v1/solve/async \
  -H "Content-Type: application/json" \
  -d '{"text": "Solve: 2x + 5 = 15"}'
```

### 4. Frontend Test

1. Visit your Vercel URL
2. Navigate to Dashboard
3. Enter a math problem
4. Verify:
   - Input modes work (Text/Image/Audio)
   - Problem solving completes
   - Agent trace appears
   - Retrieved context shows
   - Solution displays correctly

### 5. Full Integration Test

Test the complete flow:
1. **Text Input**: "What is the derivative of x²?"
2. **Verify** agent processing in trace
3. **Check** retrieved context appears
4. **Confirm** solution is correct
5. **Test** feedback buttons (Correct/Incorrect)

---

## 🐛 Troubleshooting

### Backend Issues

#### Build Fails on Render

**Problem**: `pip install` fails
**Solution**:
- Check `requirements.txt` syntax
- Ensure Python version is 3.11.0
- Check Render build logs for specific error

#### 500 Internal Server Error

**Problem**: Backend crashes on startup
**Solution**:
- Check Render logs: Dashboard → Logs
- Verify `GEMINI_API_KEY` is set correctly
- Check if all required env vars are set

#### Slow First Request (Cold Start)

**Problem**: First request takes 30+ seconds
**Solution**:
- **Free tier limitation** - Render spins down after inactivity
- Upgrade to Starter plan for always-on
- Or implement a cron job to ping `/health` every 10 minutes

#### CORS Errors

**Problem**: Frontend can't connect to backend
**Solution**:
- Check `ENVIRONMENT=production` in Render
- Verify CORS allows your Vercel domain
- Check browser console for specific error

### Frontend Issues

#### Build Fails on Vercel

**Problem**: `vite build` fails
**Solution**:
- Check build logs in Vercel dashboard
- Ensure all dependencies are in `package.json`
- Verify Node.js version compatibility

#### API Not Connecting

**Problem**: "Failed to fetch" errors
**Solution**:
- Verify `VITE_API_URL` environment variable in Vercel
- Check it matches your Render backend URL exactly
- Must include `/api/v1` at the end
- Redeploy after changing environment variables

#### Environment Variables Not Working

**Problem**: `import.meta.env.VITE_API_URL` is undefined
**Solution**:
- Environment variables MUST start with `VITE_`
- Redeploy after adding env vars (rebuild needed)
- Check Vercel settings → Environment Variables

#### 404 on Refresh

**Problem**: Refreshing a route shows 404
**Solution**:
- Already handled by `vercel.json`
- If still occurs, verify `vercel.json` is in frontend root
- Check Vercel build logs

---

## 🎯 Performance Optimization

### Backend (Render)

1. **Upgrade to Starter Plan** ($7/month)
   - No cold starts
   - Always available
   - Better performance

2. **Enable HTTP/2**
   - Automatic on Render

3. **Monitor Performance**
   - Use Render metrics dashboard
   - Set up uptime monitoring (e.g., UptimeRobot)

### Frontend (Vercel)

1. **Enable Analytics**
   - Vercel Dashboard → Analytics
   - Free tier: 100 requests/day

2. **Optimize Build**
   - Vite automatically code-splits
   - Check bundle size in build logs

3. **Enable Caching**
   - Automatic on Vercel
   - Configure cache headers if needed

---

## 🔄 Continuous Deployment

Both platforms support auto-deployment:

### On Every Git Push to Main:
1. **Backend**: Render automatically rebuilds and deploys
2. **Frontend**: Vercel automatically rebuilds and deploys

### Deployment Time:
- **Backend**: ~5-10 minutes
- **Frontend**: ~2-3 minutes

### View Deployment Status:
- **Render**: Dashboard → Deployments
- **Vercel**: Dashboard → Deployments

---

## 💰 Cost Breakdown

### Free Tier (Testing/Assignment)

| Service | Cost | Limitations |
|---------|------|-------------|
| **Render** | Free | 750 hrs/month, spins down after 15min inactivity |
| **Vercel** | Free | 100 GB bandwidth, 6000 build minutes |
| **Gemini API** | Free | 15 requests/min, 1500 requests/day |

**Total**: $0/month ✅

### Production Tier (Recommended)

| Service | Cost | Benefits |
|---------|------|----------|
| **Render Starter** | $7/month | Always-on, 512 MB RAM |
| **Vercel Pro** | Optional | Custom domains, analytics |
| **Gemini API** | Free | Same free tier |

**Total**: $7-$20/month

---

## 📝 Quick Reference

### Render Backend URL Structure
```
https://[service-name].onrender.com
```

### Vercel Frontend URL Structure
```
https://[project-name].vercel.app
```

### Environment Variables Quick Check

**Backend (Render)**:
```bash
# Check logs for loaded settings
# Should show: Starting Math_Mentor v2.0.0
# Should show: Environment: production
```

**Frontend (Vercel)**:
```javascript
// Check browser console
console.log(import.meta.env.VITE_API_URL);
// Should show: https://math-mentor-backend.onrender.com/api/v1
```

---

## 🎉 Success Checklist

- [ ] Backend deploys successfully on Render
- [ ] Health endpoint returns 200 OK
- [ ] API docs accessible at `/docs`
- [ ] Frontend deploys successfully on Vercel
- [ ] Frontend can reach backend API
- [ ] Math problem solving works end-to-end
- [ ] Agent trace displays correctly
- [ ] Feedback buttons work
- [ ] Knowledge base loads
- [ ] No CORS errors in browser console

---

## 📞 Support Resources

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **Gemini API**: https://ai.google.dev/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/

---

## 🔐 Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use environment variables** for all secrets
3. **Rotate API keys** periodically
4. **Enable HTTPS** (automatic on both platforms)
5. **Monitor API usage** to prevent abuse
6. **Set rate limits** in production (future enhancement)

---

**Deployment Complete! 🚀**

Your Math Mentor app is now live and ready for users!

**Backend**: https://math-mentor-backend.onrender.com  
**Frontend**: https://math-mentor.vercel.app

For recruiters/evaluators: Both free tiers are sufficient for demonstration and testing.
