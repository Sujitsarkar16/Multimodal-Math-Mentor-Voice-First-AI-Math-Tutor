# API Configuration Fix - URL Prefix Issue

## Problem Summary

The frontend was calling `/ingest` instead of `/api/v1/ingest`, resulting in **404 Not Found** errors in production.

### Error Details
```
POST https://multimodal-math-mentor-voice-first-ai.onrender.com/ingest 404 (Not Found)
```

## Root Cause

The backend API uses `/api/v1` prefix for all routes (defined in `server/app/api/router.py`):

```python
router = APIRouter(prefix="/api/v1")
```

However, the production build wasn't picking up the `VITE_API_URL` environment variable correctly.

## Backend API Routes Structure

All API endpoints require the `/api/v1` prefix:

### ✅ Correct URLs:
- `/api/v1/ingest` - Ingest endpoint (text, image, audio)
- `/api/v1/solve/stream` - Streaming solve
- `/api/v1/solve/async` - Async solve
- `/api/v1/solve/stats` - Pipeline statistics
- `/api/v1/solve/health` - Health check
- `/api/v1/feedback/correct` - Submit correct feedback
- `/api/v1/feedback/incorrect` - Submit incorrect feedback
- `/api/v1/feedback/hitl/approve` - HITL approval
- `/api/v1/feedback/hitl/reject` - HITL rejection
- `/api/v1/feedback/history` - Get history
- `/api/v1/feedback/entry/:id` - Get entry by ID
- `/api/v1/knowledge` - Knowledge base endpoints
- `/api/v1/knowledge/topics` - Get topics
- `/api/v1/knowledge/:id` - Get/Update/Delete entry

### ❌ Incorrect URLs (will result in 404):
- `/ingest`
- `/solve/stream`
- `/feedback/correct`
- etc.

## Solution Applied

### 1. Updated `frontend/src/services/api.js`

Added intelligent URL construction that ensures `/api/v1` is always appended:

```javascript
const getApiBase = () => {
    const envUrl = import.meta.env.VITE_API_URL;
    
    // If VITE_API_URL is set, use it
    if (envUrl) {
        // Ensure it ends with /api/v1
        return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
    }
    
    // Default to localhost for development
    return 'http://localhost:8000/api/v1';
};

const API_BASE = getApiBase();
```

This ensures that:
- If `VITE_API_URL = "https://backend.com"` → becomes `https://backend.com/api/v1`
- If `VITE_API_URL = "https://backend.com/api/v1"` → stays `https://backend.com/api/v1`
- If not set → defaults to `http://localhost:8000/api/v1`

### 2. Removed Invalid `env` Field from `vercel.json`

The `env` field in `vercel.json` doesn't work for Vite build-time variables. Environment variables must be set in Vercel's dashboard.

## Deployment Instructions

### For Vercel (Frontend):

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add a new environment variable:
   - **Name:** `VITE_API_URL`
   - **Value:** `https://multimodal-math-mentor-voice-first-ai.onrender.com`
   - **Environments:** Production, Preview, Development (check all)

4. **Important:** Do NOT include `/api/v1` in the value - the code will add it automatically

5. Redeploy your application:
   ```bash
   # Force a new deployment
   git commit --allow-empty -m "Trigger redeploy with new env vars"
   git push
   ```

### For Local Development:

Create a `.env` file in the `frontend` directory:

```env
VITE_API_URL=http://localhost:8000
```

The `/api/v1` prefix will be added automatically.

### For Render (Backend):

Ensure your backend is deployed and accessible at:
```
https://multimodal-math-mentor-voice-first-ai.onrender.com
```

No changes needed on the backend - the `/api/v1` prefix is already configured correctly.

## Testing

After deploying, verify the URLs in the browser console:

```javascript
// Open browser console on your deployed site
console.log('API Base URL:', import.meta.env.VITE_API_URL);
```

You should see:
- **Development:** `http://localhost:8000`
- **Production:** `https://multimodal-math-mentor-voice-first-ai.onrender.com`

Then test an API call and verify the full URL includes `/api/v1`:
```
✅ https://multimodal-math-mentor-voice-first-ai.onrender.com/api/v1/ingest
❌ https://multimodal-math-mentor-voice-first-ai.onrender.com/ingest
```

## Quick Reference

| Environment | VITE_API_URL Value | Final API Base |
|-------------|-------------------|----------------|
| Local Dev | `http://localhost:8000` | `http://localhost:8000/api/v1` |
| Production | `https://your-backend.onrender.com` | `https://your-backend.onrender.com/api/v1` |

## Summary

- ✅ All backend routes use `/api/v1` prefix
- ✅ Frontend code now automatically ensures `/api/v1` is included
- ✅ Set `VITE_API_URL` to just the backend domain (without `/api/v1`)
- ✅ The code handles adding `/api/v1` automatically

**Next Steps:**
1. Set the `VITE_API_URL` environment variable in Vercel dashboard
2. Redeploy your frontend
3. Test the endpoints - all 404 errors should be resolved
