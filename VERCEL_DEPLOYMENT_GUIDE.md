# TABLZ - Vercel Deployment Guide

## 🎯 Problem Solved

**Original Issue:** 404 NOT_FOUND error when deploying to Vercel
**Root Cause:** Incorrect file organization for Vercel monorepo deployment
**Solution:** Restructured project with each Next.js app at root level

---

## 📁 New Project Structure

```
tablez-demo2-allByAi/
├── reception-dashboard/     ← Next.js app (port 3000)
│   ├── src/
│   ├── package.json
│   ├── vercel.json
│   └── next.config.mjs
│
├── customer-app/            ← Next.js app (port 3001)
│   ├── src/
│   ├── package.json
│   ├── vercel.json
│   └── next.config.mjs
│
├── chef-dashboard/          ← Next.js app (port 3002)
│   ├── src/
│   ├── package.json
│   ├── vercel.json
│   └── next.config.mjs
│
├── backend/                 ← FastAPI (deploy separately)
├── frontend/                ← Original monorepo structure
└── docker-compose.yml       ← Infrastructure
```

---

## 🚀 Deployment Instructions

### Step 1: Deploy Each App Separately

**Reception Dashboard:**

```bash
cd reception-dashboard
vercel --prod
```

**Customer App:**

```bash
cd customer-app
vercel --prod
```

**Chef Dashboard:**

```bash
cd chef-dashboard
vercel --prod
```

### Step 2: Update Backend URLs

After deployment, update the backend environment variables:

```env
# In backend/.env
RECEPTION_URL=https://your-reception-app.vercel.app
CUSTOMER_URL=https://your-customer-app.vercel.app
CHEF_URL=https://your-chef-app.vercel.app
```

### Step 3: Deploy Backend Separately

Deploy the FastAPI backend to Railway, Render, or AWS:

```bash
# Example for Railway
railway login
cd backend
railway init
railway up
```

---

## 🔧 Vercel Configuration

Each app has a `vercel.json`:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "installCommand": "npm install"
}
```

---

## 📊 What Was Fixed

### ❌ Before (Causing 404)

- Monorepo with apps in `frontend/apps/`
- Workspace dependencies (`@tablz/shared`)
- No Vercel configuration
- Vercel couldn't find build commands

### ✅ After (Working)

- Each app at root level
- Local TypeScript types (no workspace deps)
- Individual `vercel.json` configs
- Standard Next.js project structure

---

## 🔍 Why This Fixes the 404

1. **File Organization:** Vercel expects Next.js apps at the root of the deployment
2. **Dependencies:** Removed unsupported workspace dependencies
3. **Configuration:** Added proper `vercel.json` for each app
4. **Build Process:** Clear build commands and output directories

---

## 🎓 Key Concepts

### Vercel Monorepo Support

- **Single Project:** One Vercel project per Next.js app
- **Not Supported:** Multiple Next.js apps in one Vercel project
- **Best Practice:** Separate deployments for each frontend app

### Workspace Dependencies

- **pnpm/npm:** Support workspace: protocol
- **Vercel:** Does not support workspace dependencies
- **Solution:** Copy types locally or publish packages

---

## 🚨 Common Mistakes to Avoid

1. **Don't:** Try to deploy multiple Next.js apps in one Vercel project
2. **Don't:** Use workspace dependencies in Vercel deployments
3. **Don't:** Put Next.js apps in subdirectories without proper config
4. **Don't:** Forget to update API URLs after deployment

---

## 📞 Next Steps

1. **Deploy each app:** Use `vercel --prod` in each directory
2. **Test deployments:** Verify each app loads correctly
3. **Update CORS:** Add Vercel domains to backend CORS settings
4. **Environment variables:** Set production API URLs
5. **Domain setup:** Configure custom domains if needed

---

## 🔗 Useful Links

- [Vercel Next.js Deployment](https://vercel.com/docs/frameworks/nextjs)
- [Vercel Monorepos](https://vercel.com/docs/concepts/projects/monorepos)
- [Railway FastAPI Deployment](https://docs.railway.app/)
- [Render FastAPI Deployment](https://docs.render.com/)

---

**Status:** ✅ READY FOR DEPLOYMENT
**Generated:** March 31, 2026
