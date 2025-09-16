# 🚀 Production Deployment Guide

This guide covers the complete production deployment process for the Poker Analytics application.

## 📋 Prerequisites

Before deploying to production, ensure you have:

- [ ] Production server (VPS/cloud instance) with Docker and Docker Compose
- [ ] Domain name pointing to your server
- [ ] SSL certificate (or ability to generate one)
- [ ] Production database credentials
- [ ] Secure secrets generated

## 🔐 Step 1: Security Setup

### 1.1 Remove Secrets from Git History

```bash
# WARNING: This rewrites git history - coordinate with your team
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch backend/mm-poker-tracker-*.json .env' \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

### 1.2 Generate Production Secrets

```bash
# Generate secure admin code (64 characters)
python -c "import secrets; print('REACT_APP_ADMIN_CODE=' + secrets.token_urlsafe(48))"

# Generate Flask secret key
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate database password
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
```

### 1.3 Create Production Environment File

```bash
# Copy template and update with your values
cp .env.production.example .env.production

# Edit with your production values
nano .env.production
```

**Required Updates:**
- `ALLOWED_ORIGINS` - Your actual domain(s)
- `POSTGRES_PASSWORD` - Strong database password
- `SECRET_KEY` - Generated secret key
- `REACT_APP_ADMIN_CODE` - Generated admin code
- `REACT_APP_PUBLIC_CODE` - 5-character game code

## 🏗️ Step 2: Server Setup

### 2.1 Install Docker and Docker Compose

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2.2 Clone Repository

```bash
git clone https://github.com/your-username/poker-analytics.git
cd poker-analytics
```

### 2.3 Set Up SSL Certificate

```bash
# Update domain in script first
nano scripts/ssl-setup.sh

# Run SSL setup
./scripts/ssl-setup.sh your-domain.com your-email@domain.com
```

## 🚀 Step 3: Deployment

### 3.1 Deploy Application

```bash
# Run deployment script
./scripts/deploy.sh production
```

The deployment script will:
- Validate environment variables
- Build frontend
- Create database backup
- Start all services
- Run database migrations
- Perform health checks

### 3.2 Verify Deployment

```bash
# Check running services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Test health endpoint
curl https://your-domain.com/api/health
```

## 🔍 Step 4: Post-Deployment Verification

### 4.1 Functional Tests

- [ ] Visit https://your-domain.com
- [ ] Test game creation: `POST /api/games/create`
- [ ] Test session upload with admin code
- [ ] Verify database connectivity
- [ ] Check SSL certificate validity

### 4.2 Security Verification

- [ ] Verify HTTPS redirects work
- [ ] Check security headers
- [ ] Test rate limiting
- [ ] Verify admin authentication

### 4.3 Performance Tests

```bash
# Basic load test (install apache2-utils first)
ab -n 100 -c 10 https://your-domain.com/api/health
```

## 📊 Step 5: Monitoring Setup

### 5.1 Enable Monitoring

The production setup includes:
- Prometheus metrics at `:9090`
- Application health checks
- Nginx status monitoring
- Database connection monitoring

### 5.2 Log Monitoring

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f backend

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx

# View system logs
tail -f /var/log/syslog
```

## 🔄 Step 6: Maintenance

### 6.1 Database Backups

```bash
# Manual backup
./scripts/backup.sh manual

# Backups are automatically created:
# - Before each deployment
# - Weekly via cron job (if set up)
```

### 6.2 SSL Certificate Renewal

```bash
# Manual renewal
./scripts/renew-ssl.sh

# Auto-renewal is set up via cron job
```

### 6.3 Application Updates

```bash
# Pull latest changes
git pull origin main

# Deploy updates
./scripts/deploy.sh production
```

## 🆘 Troubleshooting

### Common Issues

**1. SSL Certificate Issues**
```bash
# Check certificate status
sudo certbot certificates

# Manual renewal
sudo certbot renew --force-renewal
```

**2. Database Connection Issues**
```bash
# Check database container
docker-compose -f docker-compose.prod.yml logs db

# Test database connection
docker exec poker_backend_prod python -c "
from db.database import SessionLocal
from sqlalchemy import text
with SessionLocal() as db:
    result = db.execute(text('SELECT 1'))
    print('Database OK')
"
```

**3. Health Check Failures**
```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Test health endpoint locally
docker exec poker_backend_prod curl http://localhost:8000/api/health
```

**4. Performance Issues**
```bash
# Check resource usage
docker stats

# Check database performance
docker exec poker_db_prod psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC LIMIT 10;
"
```

## 🔐 Security Checklist

### Pre-Production
- [ ] Secrets removed from git history
- [ ] Strong passwords generated
- [ ] Environment variables configured
- [ ] SSL certificate installed
- [ ] Security headers enabled

### Post-Production
- [ ] HTTPS enforced
- [ ] Admin codes secure
- [ ] Database access restricted
- [ ] Logs monitored
- [ ] Backups tested
- [ ] Update procedures documented

## 📞 Support

### Log Locations
- Application logs: `./logs/poker_analytics.log`
- Deployment logs: `./logs/deploy-*.log`
- Backup logs: `./backups/backup.log`
- SSL logs: `./logs/ssl-renewal.log`

### Useful Commands

```bash
# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# View real-time logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100 backend

# Connect to database
docker exec -it poker_db_prod psql -U $POSTGRES_USER $POSTGRES_DB

# Check disk usage
df -h
du -sh ./backups

# Monitor system resources
htop
iotop
```

### Emergency Procedures

**1. Roll Back Deployment**
```bash
# Stop current containers
docker-compose -f docker-compose.prod.yml down

# Restore from backup
./scripts/restore.sh backups/latest_backup.sql.gz

# Start with previous image
# (You should tag images before deployment)
```

**2. Database Recovery**
```bash
# List available backups
ls -la backups/

# Restore specific backup
./scripts/restore.sh backups/poker_analytics_manual_YYYYMMDD_HHMMSS.sql.gz
```

## 🎯 Performance Optimization

### Database Optimization
- Regular VACUUM and ANALYZE
- Connection pooling configured
- Query optimization
- Index maintenance

### Application Optimization
- Gunicorn worker tuning
- Redis caching (optional)
- Static file optimization
- CDN integration (optional)

### Infrastructure Optimization
- Load balancing (for high traffic)
- Database replication
- Monitoring and alerting
- Auto-scaling (cloud deployments)

---

**🎉 Congratulations! Your Poker Analytics application is now running in production.**

For ongoing support and updates, refer to the troubleshooting section and maintain regular backups.