# TravelMind on ZimaOS

Deploy TravelMind on your ZimaOS device for self-hosted travel planning and journaling.

## Quick Start on ZimaOS

### 1. Prepare Your ZimaOS Device

Ensure you have:
- ZimaOS v1.2+ installed
- At least 2GB free RAM
- 10GB free storage space
- Docker and Docker Compose support enabled

### 2. Install via ZimaOS App Store (Recommended)

1. Open ZimaOS App Store
2. Search for "TravelMind"
3. Click "Install"
4. Wait for automatic deployment
5. Access via the provided URL

### 3. Manual Installation on ZimaOS

#### Clone the Repository

```bash
cd /DATA/AppData
git clone https://github.com/chicohaager/TravelMind.git
cd TravelMind
```

#### Create Environment File

```bash
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://travelmind:travelmind@db:5432/travelmind
POSTGRES_USER=travelmind
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD
POSTGRES_DB=travelmind

# Security Keys (Generate with: openssl rand -hex 32)
JWT_SECRET=CHANGE_ME_RANDOM_64_CHAR_STRING
SECRET_KEY=CHANGE_ME_ANOTHER_RANDOM_STRING

# CORS (Update with your ZimaOS IP)
CORS_ORIGINS=http://localhost:5173,http://YOUR_ZIMA_IP:5173

# Frontend API URL
VITE_API_URL=http://YOUR_ZIMA_IP:8000

# AI Features
ENABLE_AI_FEATURES=true
LOG_LEVEL=INFO
EOF
```

**Important**: Replace `YOUR_ZIMA_IP` with your ZimaOS device IP address!

#### Create Data Directories

```bash
mkdir -p /DATA/AppData/travelmind/{data,uploads,postgres,backups}
chmod -R 755 /DATA/AppData/travelmind
```

#### Deploy

```bash
docker-compose -f docker-compose.zimaos.yml up -d
```

### 4. Create Admin User

```bash
docker exec -it travelmind-backend python create_admin.py
```

Use default credentials:
- **Username**: admin
- **Password**: admin123

⚠️ **Change password after first login!**

### 5. Access TravelMind

Open your browser:
```
http://YOUR_ZIMA_IP:5173
```

Or access via ZimaOS Dashboard.

## ZimaOS-Specific Features

### Data Persistence

All data is stored in `/DATA/AppData/travelmind/`:
- **data/**: SQLite database (if not using PostgreSQL)
- **uploads/**: User-uploaded files (photos, documents)
- **postgres/**: PostgreSQL data
- **backups/**: Database backups

### Network Configuration

TravelMind runs on these ports:
- **5173**: Frontend (Web UI)
- **8000**: Backend API
- **5432**: PostgreSQL (internal network only)

### Resource Usage

Typical resource consumption:
- **RAM**: 200-400 MB (idle), up to 800 MB (active)
- **CPU**: < 5% (idle), 10-20% (active)
- **Storage**: ~500 MB (app) + your data

## ZimaOS Dashboard Integration

### Add to Dashboard

1. Open ZimaOS Dashboard
2. Click "Add Custom App"
3. Enter:
   - Name: TravelMind
   - Icon URL: `http://YOUR_ZIMA_IP:5173/icon-192.png`
   - URL: `http://YOUR_ZIMA_IP:5173`
   - Category: Productivity

### Enable Auto-Start

```bash
docker update --restart=always travelmind-backend
docker update --restart=always travelmind-frontend
docker update --restart=always travelmind-db
```

## Backup and Restore on ZimaOS

### Automatic Backups

Create backup script:

```bash
cat > /DATA/AppData/travelmind/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/DATA/AppData/travelmind/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
docker exec travelmind-db pg_dump -U travelmind travelmind > "$BACKUP_DIR/db_$DATE.sql"

# Backup uploads
tar -czf "$BACKUP_DIR/uploads_$DATE.tar.gz" /DATA/AppData/travelmind/uploads/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /DATA/AppData/travelmind/backup.sh
```

Add to cron (via ZimaOS Task Scheduler):
```
0 3 * * * /DATA/AppData/travelmind/backup.sh
```

### Manual Backup

```bash
cd /DATA/AppData/travelmind
./backup.sh
```

### Restore from Backup

```bash
# Restore database
cat /DATA/AppData/travelmind/backups/db_TIMESTAMP.sql | \
  docker exec -i travelmind-db psql -U travelmind travelmind

# Restore uploads
tar -xzf /DATA/AppData/travelmind/backups/uploads_TIMESTAMP.tar.gz -C /
```

## Updating TravelMind on ZimaOS

### Update via Git

```bash
cd /DATA/AppData/TravelMind
git pull origin main
docker-compose -f docker-compose.zimaos.yml build --no-cache
docker-compose -f docker-compose.zimaos.yml up -d
```

### Update via ZimaOS App Store

1. Open ZimaOS App Store
2. Navigate to "My Apps"
3. Find TravelMind
4. Click "Update" if available

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.zimaos.yml logs -f

# Specific service
docker-compose -f docker-compose.zimaos.yml logs -f backend
```

### Check Status

```bash
docker-compose -f docker-compose.zimaos.yml ps
```

### Resource Monitoring

Use ZimaOS Dashboard → System Monitor to view:
- CPU usage
- RAM usage
- Storage usage
- Network traffic

## Troubleshooting on ZimaOS

### Services Won't Start

1. Check if ports are available:
```bash
netstat -tuln | grep -E '5173|8000|5432'
```

2. Check Docker logs:
```bash
docker logs travelmind-backend
docker logs travelmind-frontend
docker logs travelmind-db
```

### Can't Access Web UI

1. Verify firewall settings in ZimaOS
2. Check if container is running:
```bash
docker ps | grep travelmind
```

3. Test backend health:
```bash
curl http://localhost:8000/health
```

### Database Connection Issues

1. Check if PostgreSQL is running:
```bash
docker exec -it travelmind-db pg_isready -U travelmind
```

2. Verify DATABASE_URL in `.env`

3. Check PostgreSQL logs:
```bash
docker logs travelmind-db
```

### Out of Memory

If running on low-memory ZimaOS device:

1. Reduce PostgreSQL memory in `docker-compose.zimaos.yml`:
```yaml
- "-c shared_buffers=128MB"
- "-c effective_cache_size=256MB"
```

2. Restart:
```bash
docker-compose -f docker-compose.zimaos.yml restart db
```

## Uninstall

### Remove Application

```bash
cd /DATA/AppData/TravelMind
docker-compose -f docker-compose.zimaos.yml down -v
cd ..
rm -rf TravelMind
```

### Keep Data for Reinstall

```bash
# Only stop containers, keep data
docker-compose -f docker-compose.zimaos.yml down
```

Data remains in `/DATA/AppData/travelmind/` for future use.

## Security on ZimaOS

### Network Security

1. **Use ZimaOS Firewall**: Enable firewall in Settings
2. **Restrict Access**: Use ZimaOS VPN for remote access
3. **Change Defaults**: Update all default passwords

### SSL/HTTPS

For secure access via ZimaOS reverse proxy:

1. Enable ZimaOS SSL in Network Settings
2. Add TravelMind to reverse proxy configuration
3. Access via `https://travelmind.your-zima-domain.com`

## Performance Optimization

### For Low-End ZimaOS Devices

Edit `docker-compose.zimaos.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
      reservations:
        memory: 128M
```

### For High-End ZimaOS Devices

Enable more workers:

```yaml
backend:
  command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Support

- **ZimaOS Forums**: https://community.zimaboard.com/
- **TravelMind Issues**: https://github.com/chicohaager/TravelMind/issues
- **Documentation**: See main DEPLOYMENT.md

## ZimaOS App Store Submission

If you want to submit TravelMind to ZimaOS App Store:

1. Ensure all files are in place
2. Test thoroughly on ZimaOS
3. Create `app-store.json` manifest
4. Submit to ZimaOS App Store repo

---

**Enjoy self-hosted travel planning on your ZimaOS device! 🗺️✈️**
