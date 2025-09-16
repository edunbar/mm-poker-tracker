#!/bin/bash

# SSL Certificate Setup Script for Poker Analytics
# Usage: ./scripts/ssl-setup.sh <domain> [email]

set -e

DOMAIN="$1"
EMAIL="${2:-admin@$DOMAIN}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain> [email]"
    echo "Example: $0 poker.example.com admin@example.com"
    exit 1
fi

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log "Setting up SSL certificate for domain: $DOMAIN"

# Create SSL directory
SSL_DIR="$PROJECT_ROOT/nginx/ssl"
mkdir -p "$SSL_DIR"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    log "Installing certbot..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y certbot python3-certbot-nginx
    elif command -v yum &> /dev/null; then
        sudo yum install -y certbot python3-certbot-nginx
    elif command -v brew &> /dev/null; then
        brew install certbot
    else
        error "Could not install certbot. Please install it manually."
    fi
fi

# Stop nginx if running
if docker ps | grep -q "nginx"; then
    log "Stopping nginx container..."
    docker-compose -f docker-compose.prod.yml stop nginx
fi

# Generate certificate
log "Generating SSL certificate..."
sudo certbot certonly \
    --standalone \
    --preferred-challenges http \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

if [ $? -eq 0 ]; then
    success "SSL certificate generated successfully"
else
    error "SSL certificate generation failed"
fi

# Copy certificates to nginx SSL directory
log "Copying certificates to nginx directory..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/cert.pem"
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/key.pem"

# Set proper permissions
sudo chown $USER:$USER "$SSL_DIR"/*.pem
chmod 644 "$SSL_DIR/cert.pem"
chmod 600 "$SSL_DIR/key.pem"

success "Certificates copied to nginx directory"

# Update nginx configuration with correct domain
log "Updating nginx configuration..."
sed -i.bak "s/your-domain\.com/$DOMAIN/g" "$PROJECT_ROOT/nginx/nginx.conf"
success "Nginx configuration updated"

# Create renewal script
RENEWAL_SCRIPT="$PROJECT_ROOT/scripts/renew-ssl.sh"
cat > "$RENEWAL_SCRIPT" << EOF
#!/bin/bash
# SSL Certificate Renewal Script

set -e

DOMAIN="$DOMAIN"
SSL_DIR="$SSL_DIR"

echo "Renewing SSL certificate for \$DOMAIN..."

# Stop nginx
docker-compose -f docker-compose.prod.yml stop nginx

# Renew certificate
sudo certbot renew --standalone

# Copy renewed certificates
sudo cp "/etc/letsencrypt/live/\$DOMAIN/fullchain.pem" "\$SSL_DIR/cert.pem"
sudo cp "/etc/letsencrypt/live/\$DOMAIN/privkey.pem" "\$SSL_DIR/key.pem"

# Set permissions
sudo chown $USER:$USER "\$SSL_DIR"/*.pem
chmod 644 "\$SSL_DIR/cert.pem"
chmod 600 "\$SSL_DIR/key.pem"

# Restart nginx
docker-compose -f docker-compose.prod.yml start nginx

echo "SSL certificate renewed successfully"
EOF

chmod +x "$RENEWAL_SCRIPT"
success "SSL renewal script created at: $RENEWAL_SCRIPT"

# Set up auto-renewal cron job
log "Setting up auto-renewal cron job..."
CRON_JOB="0 3 * * 0 $RENEWAL_SCRIPT >> $PROJECT_ROOT/logs/ssl-renewal.log 2>&1"

# Add to crontab if not already present
(crontab -l 2>/dev/null | grep -F "$RENEWAL_SCRIPT") || (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

success "Auto-renewal cron job configured (weekly at 3 AM on Sundays)"

# Restart nginx with SSL
log "Starting nginx with SSL configuration..."
docker-compose -f docker-compose.prod.yml start nginx

# Test SSL certificate
log "Testing SSL certificate..."
sleep 10

if curl -f "https://$DOMAIN/api/health" &> /dev/null; then
    success "SSL certificate is working correctly"
else
    warning "SSL test failed - manual verification recommended"
fi

success "SSL setup completed successfully!"
log "Your site is now available at: https://$DOMAIN"
log "Certificate will auto-renew weekly"
log "Manual renewal: $RENEWAL_SCRIPT"