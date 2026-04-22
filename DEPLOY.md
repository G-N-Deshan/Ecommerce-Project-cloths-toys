# KidZone — Vercel Deployment Guide

## Prerequisites
- GitHub account
- Vercel account (free) — https://vercel.com
- Neon account (free PostgreSQL) — https://neon.tech
- Cloudinary account (free media hosting) — https://cloudinary.com

---

## Step 1 — Push code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Create a free PostgreSQL database (Neon)

1. Go to https://neon.tech and sign up (free tier).
2. Click **New Project** → give it a name (e.g. `kidzone`).
3. Copy the **Connection String** — it looks like:
   ```
   postgresql://username:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save this — you'll use it as `DATABASE_URL` in Vercel.

---

## Step 3 — Create a free Cloudinary account

1. Go to https://cloudinary.com and sign up (free tier).
2. From your **Dashboard**, copy the **CLOUDINARY_URL** — it looks like:
   ```
   cloudinary://API_KEY:API_SECRET@CLOUD_NAME
   ```
3. Save this — you'll use it as `CLOUDINARY_URL` in Vercel.

---

## Step 4 — Deploy to Vercel

1. Go to https://vercel.com and sign in with GitHub.
2. Click **Add New → Project**.
3. Import your GitHub repository.
4. **Framework Preset**: select **Other**.
5. Click **Environment Variables** and add these:

| Variable | Value |
|---|---|
| `SECRET_KEY` | A long random string (generate one at https://djecrety.ir) |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.vercel.app,your-custom-domain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://your-project-name.vercel.app` |
| `DATABASE_URL` | The Neon connection string from Step 2 |
| `CLOUDINARY_URL` | The Cloudinary URL from Step 3 |
| `STRIPE_PUBLISHABLE_KEY` | Your Stripe publishable key |
| `STRIPE_SECRET_KEY` | Your Stripe secret key |

6. Click **Deploy**.

> **Note:** Replace `your-project-name` with the actual Vercel project name after deployment.  
> Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` with your actual `.vercel.app` domain.

---

## Step 5 — Run migrations on the production database

After the first deployment, you need to run migrations against the Neon database.

**Option A — From your local machine:**

```bash
# Set the DATABASE_URL temporarily
set DATABASE_URL=postgresql://username:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# Run migrations
python manage.py migrate

# Create a superuser for the admin panel
python manage.py createsuperuser
```

**Option B — Using Neon's SQL Editor:**

You can also use Neon's web console to run SQL directly if needed.

---

## Step 6 — Upload existing media to Cloudinary

Since Vercel has no persistent filesystem, your media files (product images, etc.)
need to be in Cloudinary.

1. Log into the **Django Admin** at `https://your-project.vercel.app/admin/`
2. Re-upload images through the admin panel — they'll automatically go to Cloudinary.

Or bulk-upload via Cloudinary's dashboard/API.

---

## How real-time updates work

A polling system automatically refreshes the frontend when you make changes in the admin panel:

1. **SiteUpdate model** tracks a timestamp (`updated_at`).
2. **Django signals** fire on every save/delete of content models (products, offers, reviews, etc.) and update the timestamp.
3. **live_reload.js** (included on every page via footer) polls `/check-updates/` every 8 seconds.
4. When the timestamp changes, the page automatically reloads — showing your admin changes in near real-time.

**No WebSockets or external services needed.** Works within Vercel's free tier.

---

## Redeployment

Every `git push` to `main` triggers an automatic redeployment on Vercel.

```bash
git add .
git commit -m "Update something"
git push
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Static files not loading | Make sure `whitenoise` is in middleware and `STATIC_ROOT` is set |
| 500 error on Vercel | Check Vercel **Function Logs** in the dashboard |
| Images not showing | Verify `CLOUDINARY_URL` is set correctly in env vars |
| Admin login not working | Run `python manage.py createsuperuser` against the production DB |
| CSRF errors | Add your Vercel domain to `CSRF_TRUSTED_ORIGINS` |
| Database errors | Check `DATABASE_URL` is correct and Neon project is active |

---

## Environment Variables Reference

See `.env.example` for the full list of supported environment variables.
