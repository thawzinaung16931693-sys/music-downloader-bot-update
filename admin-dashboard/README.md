# Bar Lar Lar Admin Dashboard

🎮 Vaporwave Cyberpunk themed admin dashboard for managing the Telegram music bot.

## Features

✅ **User Management** - View, ban, message users  
✅ **Dashboard Analytics** - Real-time stats and charts  
✅ **Subscription Management** - Plans and trials (coming soon)  
✅ **Telegram OAuth** - Secure login with Telegram  
✅ **Responsive Design** - Works on desktop and mobile  
✅ **Cyberpunk Theme** - Pink/Cyan neon aesthetic  

## Tech Stack

**Backend:**
- FastAPI (Python)
- SQLite + SQLAlchemy
- JWT Authentication
- Async/Await

**Frontend:**
- React + TypeScript
- Vite
- TailwindCSS
- TanStack Query
- Zustand

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m app.main
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
# Frontend available at http://localhost:5173
```

## Production Deployment

### Prerequisites

1. GCP VM with nginx installed
2. Telegram bot token
3. Admin user IDs

### Deploy to GCP

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

This will:
1. Upload backend files to VM
2. Install Python dependencies
3. Setup systemd service
4. Build and upload frontend
5. Configure nginx

### Manual Deployment Steps

#### 1. Setup Backend

```bash
# SSH to VM
gcloud compute ssh instance-20260906-175024 --zone=us-central1-a

# Create directory
sudo mkdir -p /opt/telegram-music-bot/admin-dashboard
sudo chown musicbot:musicbot /opt/telegram-music-bot/admin-dashboard

# Switch to musicbot user
sudo -u musicbot bash

# Upload files (from local machine)
gcloud compute scp --recurse ./admin-dashboard musicbot@instance:~/ --zone=us-central1-a

# Move to correct location
mv ~/admin-dashboard/* /opt/telegram-music-bot/admin-dashboard/

# Setup backend
cd /opt/telegram-music-bot/admin-dashboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Generate JWT secret
openssl rand -hex 32
# Copy to .env file

# Initialize database
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

#### 2. Setup Systemd Service

```bash
# Copy service file
sudo cp /opt/telegram-music-bot/admin-dashboard/backend/admin-dashboard.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable admin-dashboard
sudo systemctl start admin-dashboard

# Check status
sudo systemctl status admin-dashboard
```

#### 3. Build and Deploy Frontend

```bash
# On local machine
cd frontend
npm install
npm run build

# Upload to VM
gcloud compute scp --recurse ./dist musicbot@instance:/opt/telegram-music-bot/admin-dashboard/frontend/ --zone=us-central1-a
```

#### 4. Configure Nginx

```bash
# SSH to VM
sudo nano /etc/nginx/sites-available/admin-dashboard

# Add configuration:
server {
    listen 8080;
    server_name _;

    # Frontend
    location / {
        root /opt/telegram-music-bot/admin-dashboard/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# Enable site
sudo ln -sf /etc/nginx/sites-available/admin-dashboard /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

#### 5. Open Firewall Port

```bash
gcloud compute firewall-rules create admin-dashboard-8080 \
  --allow tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server \
  --project gen-lang-client-0815462248
```

## Access

🌐 **URL:** http://35.222.57.236:8080

Login with your Telegram account. Only authorized admin user IDs can access.

## Configuration

### Backend (.env)

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_IDS=123456789,987654321
JWT_SECRET_KEY=generated_secret
DATABASE_URL=sqlite+aiosqlite:///./admin_dashboard.db
CORS_ORIGINS=http://localhost:5173,http://35.222.57.236:8080
```

### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_TELEGRAM_BOT_USERNAME=barlarlaraimusicdownloader_bot
```

## Authorized Admins

Current admin user IDs:
- 8384421614
- 8852793220
- 8048554449
- 8796245974

To add more admins, update `ADMIN_USER_IDS` in backend `.env` and restart service.

## Troubleshooting

### Backend not starting

```bash
sudo journalctl -u admin-dashboard -f
```

### Database issues

```bash
# Delete and recreate
cd /opt/telegram-music-bot/admin-dashboard/backend
rm admin_dashboard.db
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

### Frontend not loading

Check nginx logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

### CORS errors

Update CORS_ORIGINS in backend `.env` to include your frontend URL.

## Development Roadmap

- [x] Dashboard overview
- [x] User management
- [x] Telegram OAuth
- [ ] Subscription plan editor
- [ ] Trial campaign manager
- [ ] Advanced analytics
- [ ] Admin role management
- [ ] Bulk user operations
- [ ] Export reports

## Security Notes

⚠️ **Important:**
- Change JWT_SECRET_KEY in production
- Use HTTPS in production (setup SSL certificate)
- Restrict firewall rules to specific IPs if possible
- Regularly backup the database
- Monitor admin access logs

## License

Proprietary - Bar Lar Lar Music Bot
