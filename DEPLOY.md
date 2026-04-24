# KidZone — DigitalOcean Deployment Guide

## Prerequisites
- DigitalOcean droplet (Ubuntu 22.04+)
- Domain name (optional but recommended)
- GitHub repository access

---

## 1. Prepare Server

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx
```

Clone the project:

```bash
git clone <your-repo-url> kidzone
cd kidzone
```

---

## 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Configure Environment Variables

Create `.env` in project root (or export variables in systemd):

```env
SECRET_KEY=your-secret
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,server-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

# Choose one DB style:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
# or MySQL fallback values:
DB_NAME=myproject
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=3306

# Optional services
CLOUDINARY_URL=cloudinary://...
STRIPE_PUBLISHABLE_KEY=...
STRIPE_SECRET_KEY=...
```

---

## 4. Run Django Setup

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

---

## 5. Configure Gunicorn Service

Create `/etc/systemd/system/kidzone.service`:

```ini
[Unit]
Description=KidZone Django App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/kidzone
Environment="PATH=/var/www/kidzone/.venv/bin"
ExecStart=/var/www/kidzone/.venv/bin/gunicorn myproject.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kidzone
sudo systemctl start kidzone
sudo systemctl status kidzone
```

---

## 6. Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/kidzone`:

```nginx
server {
   listen 80;
   server_name your-domain.com www.your-domain.com;

   location /static/ {
      alias /var/www/kidzone/staticfiles/;
   }

   location /media/ {
      alias /var/www/kidzone/media/;
   }

   location / {
      proxy_pass http://127.0.0.1:8000;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
   }
}
```

Enable config and reload:

```bash
sudo ln -s /etc/nginx/sites-available/kidzone /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7. Enable HTTPS (Recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

## 8. Deploy Updates

```bash
cd /var/www/kidzone
git pull
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart kidzone
sudo systemctl reload nginx
```
