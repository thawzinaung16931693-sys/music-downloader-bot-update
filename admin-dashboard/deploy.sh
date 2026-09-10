#!/bin/bash

# Deployment script for admin dashboard

echo "🚀 Deploying Admin Dashboard to GCP VM..."

# Variables
VM_NAME="instance-20260906-175024"
ZONE="us-central1-a"
PROJECT="gen-lang-client-0815462248"
REMOTE_USER="musicbot"
REMOTE_PATH="/opt/telegram-music-bot/admin-dashboard"

# Step 1: Upload backend files
echo "📦 Uploading backend files..."
gcloud compute scp --recurse ./backend ${REMOTE_USER}@${VM_NAME}:${REMOTE_PATH}/ \
  --zone=${ZONE} --project=${PROJECT}

# Step 2: Install backend dependencies
echo "📦 Installing backend dependencies..."
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --command="
  sudo -u ${REMOTE_USER} bash << 'EOF'
    cd ${REMOTE_PATH}/backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
EOF
"

# Step 3: Generate JWT secret
echo "🔐 Generating JWT secret..."
JWT_SECRET=$(openssl rand -hex 32)
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --command="
  sudo -u ${REMOTE_USER} bash << 'EOF'
    cd ${REMOTE_PATH}/backend
    sed -i 's/your-secret-key-change-this-in-production/${JWT_SECRET}/g' .env
EOF
"

# Step 4: Setup systemd service
echo "⚙️ Setting up systemd service..."
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --command="
  sudo cp ${REMOTE_PATH}/backend/admin-dashboard.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable admin-dashboard
  sudo systemctl restart admin-dashboard
"

# Step 5: Build and upload frontend
echo "🎨 Building frontend..."
cd frontend
npm install
npm run build

echo "📦 Uploading frontend..."
gcloud compute scp --recurse ./dist ${REMOTE_USER}@${VM_NAME}:${REMOTE_PATH}/frontend/ \
  --zone=${ZONE} --project=${PROJECT}

# Step 6: Configure nginx
echo "🌐 Configuring nginx..."
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --project=${PROJECT} --command="
  sudo bash << 'EOF'
    cat > /etc/nginx/sites-available/admin-dashboard << 'NGINX'
server {
    listen 8080;
    server_name _;

    # Frontend
    location / {
        root ${REMOTE_PATH}/frontend/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
NGINX

    ln -sf /etc/nginx/sites-available/admin-dashboard /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
EOF
"

echo "✅ Deployment complete!"
echo ""
echo "🌐 Admin dashboard is now available at:"
echo "   http://35.222.57.236:8080"
echo ""
echo "📊 Check backend status: sudo systemctl status admin-dashboard"
echo "📋 View backend logs: sudo journalctl -u admin-dashboard -f"
