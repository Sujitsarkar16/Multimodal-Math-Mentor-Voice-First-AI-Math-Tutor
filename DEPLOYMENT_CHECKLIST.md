# Quick Deployment Checklist

Use this checklist when deploying Math Mentor to Vercel and Render.

## Pre-Deployment

- [ ] All code committed and pushed to GitHub
- [ ] `.gitignore` excludes `.env` files
- [ ] Backend has `render.yaml` configuration
- [ ] Frontend has `vercel.json` configuration
- [ ] Gemini API key obtained from Google AI Studio

## Backend Deployment (Render)

### Initial Setup
- [ ] Create Render account
- [ ] Connect GitHub repository
- [ ] Create new Web Service
- [ ] Set root directory to `server`
- [ ] Configure build command: `pip install -r requirements.txt`
- [ ] Configure start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables (Required)
- [ ] `PYTHON_VERSION` = `3.11.0`
- [ ] `ENVIRONMENT` = `production`
- [ ] `GEMINI_API_KEY` = [Your API Key]
- [ ] `LOG_LEVEL` = `INFO`
- [ ] `DEFAULT_LLM_MODEL` = `gemini-2.0-flash-exp`

### Deployment
- [ ] Click "Create Web Service"
- [ ] Wait for deployment (5-10 minutes)
- [ ] Test health endpoint: `/health`
- [ ] Copy backend URL for frontend config

## Frontend Deployment (Vercel)

### Initial Setup
- [ ] Create Vercel account
- [ ] Import GitHub repository
- [ ] Set framework preset to `Vite`
- [ ] Set root directory to `frontend`
- [ ] Build command auto-detected: `npm run build`
- [ ] Output directory auto-detected: `dist`

### Environment Variables (Required)
- [ ] `VITE_API_URL` = [Your Render Backend URL]/api/v1

### Deployment
- [ ] Click "Deploy"
- [ ] Wait for deployment (2-3 minutes)
- [ ] Test frontend loads correctly
- [ ] Test API connectivity

## Post-Deployment Testing

### Backend Tests
- [ ] Health check returns 200 OK
- [ ] `/docs` loads API documentation
- [ ] Test solve endpoint with sample problem
- [ ] Check logs for errors

### Frontend Tests
- [ ] App loads without errors
- [ ] Navigate to Dashboard
- [ ] Test text input
- [ ] Verify agent trace appears
- [ ] Check retrieved context displays
- [ ] Test feedback buttons
- [ ] Inspect browser console (no CORS errors)

### Integration Tests
- [ ] Submit math problem
- [ ] Verify streaming updates work
- [ ] Check solution accuracy
- [ ] Test all input modes (text/image/audio)
- [ ] Verify history saves correctly

## Troubleshooting

### If backend won't start:
1. Check Render logs
2. Verify all required env vars are set
3. Confirm GEMINI_API_KEY is valid
4. Check Python version is 3.11.0

### If frontend can't reach backend:
1. Verify VITE_API_URL in Vercel settings
2. Check CORS is enabled in backend
3. Confirm `/api/v1` suffix in URL
4. Redeploy frontend after env var changes

### If build fails:
1. Check build logs in dashboard
2. Verify all dependencies in requirements.txt/package.json
3. Confirm file paths and directory structure
4. Check for syntax errors

## Success Indicators

✅ Backend health endpoint returns healthy status
✅ Frontend loads without console errors
✅ API calls succeed (check Network tab)
✅ Math problems solve correctly
✅ Agent trace displays in UI
✅ Feedback system works
✅ No CORS errors

## Cost Summary

**Free Tier (Perfect for assignments):**
- Render: Free (750 hrs/month)
- Vercel: Free (100 GB bandwidth)
- Gemini API: Free (1500 requests/day)
- **Total: $0/month**

**Production Tier:**
- Render Starter: $7/month
- Vercel Pro: Optional
- **Total: $7-20/month**

## URLs to Save

- **Backend**: https://[your-service].onrender.com
- **Frontend**: https://[your-project].vercel.app
- **API Docs**: https://[your-service].onrender.com/docs

## Next Steps After Deployment

1. Test all features thoroughly
2. Monitor error logs
3. Set up uptime monitoring (optional)
4. Share links with recruiters/evaluators
5. Prepare demo script

---

**For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)**
