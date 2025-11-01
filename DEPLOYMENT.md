# TravelMind - Deployment Guide

This guide explains how to deploy TravelMind in production.

## Prerequisites

- Docker and Docker Compose installed
- Domain name (optional, but recommended)
- SSL certificate (optional, for HTTPS)
- At least 2GB RAM and 10GB disk space

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/chicohaager/TravelMind.git
cd TravelMind
```

### 2. Configure Environment

Create a `.env.prod` file with your production settings:

```bash
cp .env.example .env.prod
nano .env.prod
```

**Important Environment Variables:**

```env
# Database
DATABASE_URL=postgresql://travelmind:CHANGE_ME@db:5432/travelmind
POSTGRES_USER=travelmind
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=travelmind

# Security
JWT_SECRET=CHANGE_ME_RANDOM_STRING_64_CHARS
SECRET_KEY=CHANGE_ME_ANOTHER_RANDOM_STRING

# CORS (your domain)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Frontend
VITE_API_URL=https://yourdomain.com/api

# Optional: AI Features (users configure their own keys in Settings)
ENABLE_AI_FEATURES=true
```

**Generate secure secrets:**

```bash
# For JWT_SECRET and SECRET_KEY
openssl rand -hex 32
```

### 3. Deploy with One Command

```bash
./deploy.sh
```

This script will:
- Build production Docker images
- Stop existing containers
- Start new containers
- Show service status

### 4. Create Admin User

```bash
docker exec -it travelmind-backend-prod python create_admin.py
```

Default credentials:
- **Username**: admin
- **Password**: admin123
- **Email**: admin@travelmind.local

⚠️ **Change the admin password immediately after first login!**

## Manual Deployment

### Build and Start

```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### View Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Stop Services

```bash
docker-compose -f docker-compose.prod.yml down
```

## Production Architecture

```
┌─────────────┐
│   Internet  │
└──────┬──────┘
       │
┌──────▼──────────┐
│  Nginx (Optional)|  Port 80/443
│   Reverse Proxy  │
└──────┬──────────┘
       │
┌──────▼──────────┐
│   Frontend      │  Port 80
│  (React/Vite)   │
└──────┬──────────┘
       │
┌──────▼──────────┐
│    Backend      │  Port 8000
│   (FastAPI)     │
└──────┬──────────┘
       │
┌──────▼──────────┐
│   PostgreSQL    │  Port 5432
└─────────────────┘
```

## Database Management

### Backup Database

```bash
docker exec travelmind-db-prod pg_dump -U travelmind travelmind > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database

```bash
cat backup_file.sql | docker exec -i travelmind-db-prod psql -U travelmind travelmind
```

### Access Database

```bash
docker exec -it travelmind-db-prod psql -U travelmind -d travelmind
```

## SSL/HTTPS Setup (Optional but Recommended)

### Using Certbot (Let's Encrypt)

1. Install Certbot:
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

2. Get SSL certificate:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

3. Auto-renewal:
```bash
sudo certbot renew --dry-run
```

## Monitoring and Maintenance

### Check Service Health

```bash
docker-compose -f docker-compose.prod.yml ps
```

### View Resource Usage

```bash
docker stats
```

### Restart Specific Service

```bash
docker-compose -f docker-compose.prod.yml restart backend
```

### Update Application

```bash
git pull origin main
./deploy.sh
```

## Troubleshooting

### Services Won't Start

Check logs:
```bash
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
docker-compose -f docker-compose.prod.yml logs db
```

### Database Connection Issues

1. Check DATABASE_URL in .env.prod
2. Ensure PostgreSQL is running:
```bash
docker ps | grep travelmind-db-prod
```

### Frontend Can't Connect to Backend

1. Check VITE_API_URL in .env.prod
2. Check CORS_ORIGINS includes your domain
3. Verify backend is accessible:
```bash
curl http://localhost:8000/health
```

## Security Checklist

- [✓] Change all default passwords
- [✓] Use strong SECRET_KEY and JWT_SECRET
- [✓] Enable HTTPS with valid SSL certificate
- [✓] Set restrictive CORS_ORIGINS
- [✓] Keep Docker images updated
- [✓] Regular database backups
- [✓] Use environment variables for secrets
- [✓] Monitor logs for suspicious activity

## Performance Optimization

### Database Optimization

Add indexes for frequently queried fields:
```sql
CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_diary_trip_id ON diary_entries(trip_id);
CREATE INDEX idx_places_trip_id ON places(trip_id);
```

### Frontend Optimization

The production build is automatically optimized with:
- Minification
- Tree shaking
- Code splitting
- Asset compression

### Backend Optimization

Uvicorn workers (edit backend/Dockerfile.prod):
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Backup Strategy

### Automated Backups

Create a cron job:
```bash
crontab -e
```

Add:
```
0 2 * * * /path/to/TravelMind/backup.sh
```

Create backup.sh:
```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker exec travelmind-db-prod pg_dump -U travelmind travelmind > "$BACKUP_DIR/db_$DATE.sql"

# Backup uploads
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" uploads/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/chicohaager/TravelMind/issues
- Documentation: https://github.com/chicohaager/TravelMind/wiki

## License

See LICENSE file for details.
