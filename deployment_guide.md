# Complete Production Deployment Guide - UniVo (community_builders)

This guide provides step-by-step instructions to deploy your Django application, **UniVo**, live. It covers deployment on modern PaaS platforms (Render), shared Python environments (PythonAnywhere), and full, step-by-step instructions for setting up a production-ready **Linux VPS (Ubuntu)**.

---

## Table of Contents
1. [Environment Variables and Security Setup](#1-environment-variables-and-security-setup)
2. [Option A: Deploying on Render (PaaS)](#2-option-a-deploying-on-render-paas)
3. [Option B: Deploying on PythonAnywhere (Shared Hosting)](#3-option-b-deploying-on-pythonanywhere-shared-hosting)
4. [Option C: Step-by-Step Linux VPS Setup (Ubuntu + Nginx + Gunicorn + Postgres + SSL)](#4-option-c-step-by-step-linux-vps-setup-ubuntu--nginx--gunicorn--postgres--ssl)
   - [Phase 1: Initial Server Security & Firewall](#phase-1-initial-server-security--firewall)
   - [Phase 2: Installing & Configuring PostgreSQL](#phase-2-installing--configuring-postgresql)
   - [Phase 3: Deploying Code and Dependencies](#phase-3-deploying-code-and-dependencies)
   - [Phase 4: Setting Up Gunicorn (Systemd Service)](#phase-4-setting-up-gunicorn-systemd-service)
   - [Phase 5: Setting Up Nginx Reverse Proxy](#phase-5-setting-up-nginx-reverse-proxy)
   - [Phase 6: Securing the App with SSL (Let's Encrypt)](#phase-6-securing-the-app-with-ssl-lets-encrypt)
   - [Phase 7: Automating Future Deployments](#phase-7-automating-future-deployments)
   - [Phase 8: Troubleshooting and Log Management](#phase-8-troubleshooting-and-log-management)

---

## 1. Environment Variables and Security Setup

The project uses `python-decouple` to pull configurations from environment variables.
1. **Local Setup**: Copy `.env.example` to `.env` in the root directory:
   ```bash
   copy .env.example .env
   ```
2. **Production Setup**:
   - Do **NOT** upload your `.env` file containing secret keys to GitHub.
   - For Render and PythonAnywhere, you will define these settings in their dashboards.
   - For VPS, you will write them into a protected `.env` file on the server.

---

## 2. Option A: Deploying on Render (PaaS)

Render manages database administration and server configuration for you.

### Step 1: Create a PostgreSQL Database on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **PostgreSQL**.
3. Set **Name** to `univo-db` and click **Create Database**.
4. Copy the **Internal Database URL** (e.g. `postgres://user:password@host/dbname`).

### Step 2: Create a Web Service
1. Click **New +** -> **Web Service** and connect your Git repository.
2. Configure settings:
   - **Language**: `Python`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**:
     ```bash
     gunicorn community_builders.wsgi:application
     ```

### Step 3: Configure Environment Variables
In the service settings, add these variables:
- `DEBUG` = `False`
- `SECRET_KEY` = `(Generate a secure unique key)`
- `ALLOWED_HOSTS` = `your-subdomain.onrender.com,yourdomain.com`
- `DATABASE_URL` = `(Your copied Internal Database URL)`
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`

Click **Save** and wait for Render to build and host your service.

---

## 3. Option B: Deploying on PythonAnywhere (Shared Hosting)

PythonAnywhere allows running Django with persistent storage, which is ideal if you want to keep the local SQLite database (`db.sqlite3`).

### Step 1: Clone the Project
Open a Bash console in PythonAnywhere and run:
```bash
git clone <your-git-repo-url> community_builders
cd community_builders
```

### Step 2: Set Up Virtual Environment & Database
```bash
mkvirtualenv --python=/usr/bin/python3.10 univo-env
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

### Step 3: Configure WSGI
On the Web Dashboard:
1. Under **Virtualenv**, set `/home/yourusername/.virtualenvs/univo-env`.
2. Under **Code**, edit your WSGI configuration file:
   ```python
   import os
   import sys
   path = '/home/yourusername/community_builders'
   if path not in sys.path:
       sys.path.insert(0, path)
   os.environ['DJANGO_SETTINGS_MODULE'] = 'community_builders.settings'
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

### Step 4: Map Static Files
Scroll down to the **Static files** section:
- **URL**: `/static/` -> **Path**: `/home/yourusername/community_builders/staticfiles`
- **URL**: `/media/` -> **Path**: `/home/yourusername/community_builders/media`

Reload your web app to publish it.

---

## 4. Option C: Step-by-Step Linux VPS Setup (Ubuntu + Nginx + Gunicorn + Postgres + SSL)

This is a complete, manual guide for a clean Ubuntu 22.04 / 24.04 server.

---

### Phase 1: Initial Server Security & Firewall
Always configure a non-root sudo user and enable a firewall to prevent malicious access.

1. **Connect to your server as root**:
   ```bash
   ssh root@your_server_ip
   ```
2. **Create a new deployment user** (e.g., `deploy`):
   ```bash
   adduser deploy
   ```
   *(Enter a strong password when prompted)*
3. **Grant sudo permissions**:
   ```bash
   usermod -aG sudo deploy
   ```
4. **Configure Firewall (UFW)**:
   Restrict access to all ports except SSH, HTTP, and HTTPS:
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow OpenSSH
   ufw allow 'Nginx Full'
   ufw enable
   ```
   *(Type `y` and press enter to confirm)*
5. **Switch to the new user**:
   ```bash
   su - deploy
   ```

---

### Phase 2: Installing & Configuring PostgreSQL
Production environments should use an enterprise-grade database like PostgreSQL instead of SQLite.

1. **Install PostgreSQL and dependencies**:
   ```bash
   sudo apt update
   sudo apt install postgresql postgresql-contrib libpq-dev python3-dev -y
   ```
2. **Access PostgreSQL command line**:
   ```bash
   sudo -i -u postgres psql
   ```
3. **Create Database, User, and Grant Privileges**:
   Run the following commands inside the PostgreSQL prompt (replace placeholders with secure values):
   ```sql
   CREATE DATABASE univo_db;
   CREATE USER univo_user WITH PASSWORD 'choose_a_strong_password';
   ALTER ROLE univo_user SET client_encoding TO 'utf8';
   ALTER ROLE univo_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE univo_user SET timezone TO 'Asia/Kolkata';
   GRANT ALL PRIVILEGES ON DATABASE univo_db TO univo_user;
   \q
   ```
4. **Enable PostgreSQL service**:
   ```bash
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

---

### Phase 3: Deploying Code and Dependencies

1. **Install Git, Pip, and Virtualenv**:
   ```bash
   sudo apt install git python3-pip python3-venv -y
   ```
2. **Create Web Root and Clone Repository**:
   ```bash
   sudo mkdir -p /var/www/community_builders
   sudo chown -R deploy:deploy /var/www/community_builders
   git clone <your-git-repo-url> /var/www/community_builders
   cd /var/www/community_builders
   ```
3. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. **Install Requirements**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. **Create Server `.env` File**:
   ```bash
   nano /var/www/community_builders/.env
   ```
   Paste the following credentials:
   ```env
   DEBUG=False
   SECRET_KEY=generate_your_unique_secret_key_here
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your_server_ip
   DATABASE_URL=postgres://univo_user:choose_a_strong_password@127.0.0.1:5432/univo_db
   
   # Add your Google/Razorpay API Keys below
   GOOGLE_CLIENT_ID=your_id
   GOOGLE_CLIENT_SECRET=your_secret
   GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback/
   RAZORPAY_KEY_ID=your_key
   RAZORPAY_KEY_SECRET=your_secret
   ```
   Save and close: `Ctrl+O`, `Enter`, `Ctrl+X`.
6. **Set up Folders, Permissions, Migrations**:
   Run these inside the virtual environment:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

---

### Phase 4: Setting Up Gunicorn (Systemd Service)
We use Systemd to automatically start Gunicorn when the server boots, and socket activation for performance.

1. **Create Gunicorn Socket File**:
   ```bash
   sudo nano /etc/systemd/system/gunicorn.socket
   ```
   Paste:
   ```ini
   [Unit]
   Description=gunicorn socket

   [Socket]
   ListenStream=/run/gunicorn.sock

   [Install]
   WantedBy=sockets.target
   ```
2. **Create Gunicorn Service File**:
   ```bash
   sudo nano /etc/systemd/system/gunicorn.service
   ```
   Paste:
   ```ini
   [Unit]
   Description=gunicorn daemon
   Requires=gunicorn.socket
   After=network.target

   [Service]
   User=deploy
   Group=www-data
   WorkingDirectory=/var/www/community_builders
   ExecStart=/var/www/community_builders/venv/bin/gunicorn \
             --access-logfile - \
             --workers 3 \
             --bind unix:/run/gunicorn.sock \
             community_builders.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```
3. **Start and Enable Gunicorn**:
   ```bash
   sudo systemctl start gunicorn.socket
   sudo systemctl enable gunicorn.socket
   ```

---

### Phase 5: Setting Up Nginx Reverse Proxy
Nginx acts as a high-performance front server, serving static/media files directly and proxying app requests to Gunicorn.

1. **Install Nginx**:
   ```bash
   sudo apt install nginx -y
   ```
2. **Create Nginx Site Configuration**:
   ```bash
   sudo nano /etc/nginx/sites-available/community_builders
   ```
   Paste the following:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;

       location = /favicon.ico { access_log off; log_not_found off; }

       # Serve static files directly
       location /static/ {
           alias /var/www/community_builders/staticfiles/;
       }

       # Serve media uploads directly
       location /media/ {
           alias /var/www/community_builders/media/;
       }

       # Proxy HTTP requests to Gunicorn socket
       location / {
           include proxy_params;
           proxy_pass http://unix:/run/gunicorn.sock;
       }
   }
   ```
3. **Configure Permissions for Nginx**:
   For Nginx (`www-data` group) to read files in your deploy folder:
   ```bash
   sudo usermod -aG deploy www-data
   chmod 710 /var/www/community_builders
   ```
4. **Enable Site & Test Config**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/community_builders /etc/nginx/sites-enabled/
   # Test Nginx syntax
   sudo nginx -t
   ```
   *(You should see: `syntax is ok` and `test is successful`)*
5. **Restart Nginx**:
   ```bash
   sudo systemctl restart nginx
   sudo systemctl remove /etc/nginx/sites-enabled/default
   ```

---

### Phase 6: Securing the App with SSL (Let's Encrypt)
Free and automated SSL setup using Certbot.

1. **Install Certbot and Nginx plugin**:
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   ```
2. **Generate SSL Certificate**:
   ```bash
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```
   - Enter your email address.
   - Agree to terms.
   - Certbot will automatically rewrite the Nginx file to enable HTTPS redirection.
3. **Verify Auto-Renewal**:
   Certbot installs a cron job that automatically renews the SSL certificates before they expire. Test it:
   ```bash
   sudo certbot renew --dry-run
   ```

---

### Phase 7: Automating Future Deployments
To update your live site without performing manual commands, create a script `deploy.sh` in `/var/www/community_builders/deploy.sh`:

1. **Create deploy script**:
   ```bash
   nano /var/www/community_builders/deploy.sh
   ```
   Paste:
   ```bash
   #!/usr/bin/env bash
   cd /var/www/community_builders
   
   echo "Pulling latest code from Git..."
   git pull origin main

   echo "Activating virtualenv..."
   source venv/bin/activate

   echo "Installing packages..."
   pip install -r requirements.txt

   echo "Running migrations..."
   python manage.py migrate

   echo "Collecting static assets..."
   python manage.py collectstatic --noinput

   echo "Restarting Gunicorn server..."
   sudo systemctl restart gunicorn

   echo "Deployment successful!"
   ```
2. **Make it executable**:
   ```bash
   chmod +x /var/www/community_builders/deploy.sh
   ```
3. **Run updates in the future**:
   ```bash
   ./deploy.sh
   ```

---

### Phase 8: Troubleshooting and Log Management

If things go wrong, use these command lines to find the source of errors:

* **View live Gunicorn application logs**:
  ```bash
  sudo journalctl -u gunicorn --no-pager -n 50
  ```
* **View live Nginx access and error logs**:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```
* **Restart services after config edits**:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl restart gunicorn
  sudo systemctl restart nginx
  ```
