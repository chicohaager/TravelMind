# TravelMind - Docker Hub Deployment

Deploy TravelMind using pre-built Docker images from Docker Hub.

## Quick Start with Docker Hub

### 1. Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM and 10GB disk space

### 2. Download Configuration

```bash
# Download docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/chicohaager/TravelMind/main/docker-compose.hub.yml

# Download environment example
curl -O https://raw.githubusercontent.com/chicohaager/TravelMind/main/.env.example
```

### 3. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env
nano .env
```

**Minimum required settings:**

```env
# Security (IMPORTANT: Change these!)
JWT_SECRET=your_random_64_char_string
SECRET_KEY=another_random_64_char_string

# Database
POSTGRES_PASSWORD=secure_password_here

# CORS (your domain or IP)
CORS_ORIGINS=http://localhost:5173,http://your-domain.com
```

**Generate secure secrets:**
```bash
openssl rand -hex 32
```

### 4. Deploy

```bash
docker-compose -f docker-compose.hub.yml up -d
```

### 5. Create Admin User

```bash
docker exec -it travelmind-backend-prod python create_admin.py
```

Default credentials:
- Username: `admin`
- Password: `admin123`

**⚠️ Change password after first login!**

### 6. Access Application

Open your browser:
```
http://localhost
```

Backend API: `http://localhost:8000`

## Available Images

### Backend Image
```
docker pull chicohaager/travelmind-backend:latest
```

### Frontend Image
```
docker pull chicohaager/travelmind-frontend:latest
```

## Image Tags

- `latest` - Latest stable release
- `v1.0.0` - Specific version (when available)

## Update to Latest Version

```bash
# Pull latest images
docker-compose -f docker-compose.hub.yml pull

# Restart services
docker-compose -f docker-compose.hub.yml up -d
```

## Environment Variables

### Backend Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://...` | Database connection string |
| `JWT_SECRET` | - | **Required** - JWT token secret |
| `SECRET_KEY` | - | **Required** - Encryption secret |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_AI_FEATURES` | `true` | Enable AI features |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `travelmind` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `travelmind` | **Change in production!** |
| `POSTGRES_DB` | `travelmind` | Database name |

## Storage and Persistence

Data is stored in Docker volumes:
- `postgres_data` - Database data
- `./data` - SQLite backup and logs
- `./uploads` - User-uploaded files

To backup your data:
```bash
# Backup database
docker exec travelmind-db-prod pg_dump -U travelmind travelmind > backup.sql

# Backup uploads
tar -czf uploads-backup.tar.gz uploads/
```

## Troubleshooting

### Services won't start

Check logs:
```bash
docker-compose -f docker-compose.hub.yml logs -f
```

### Database connection issues

Verify DATABASE_URL in `.env` matches your PostgreSQL settings.

### Frontend can't reach backend

Check CORS_ORIGINS includes your domain/IP:
```env
CORS_ORIGINS=http://localhost:5173,http://your-ip:5173
```

## Advanced Configuration

### Custom Ports

Edit `docker-compose.hub.yml`:
```yaml
services:
  backend:
    ports:
      - "8080:8000"  # Custom backend port
  frontend:
    ports:
      - "3000:80"    # Custom frontend port
```

### Using External Database

Update `.env`:
```env
DATABASE_URL=postgresql://user:pass@external-host:5432/dbname
```

Then remove the `db` service from `docker-compose.hub.yml`.

## Building Your Own Images

If you want to build from source:

```bash
# Clone repository
git clone https://github.com/chicohaager/TravelMind.git
cd TravelMind

# Build images
./build-docker-images.sh v1.0.0

# Push to your own Docker Hub account (optional)
# Edit scripts with your Docker Hub username first
./push-docker-images.sh v1.0.0
```

## Support

- **Issues**: https://github.com/chicohaager/TravelMind/issues
- **Documentation**: https://github.com/chicohaager/TravelMind
- **Docker Hub**: https://hub.docker.com/u/chicohaager

## License

See LICENSE file in the repository.

---

**Happy traveling with TravelMind! 🗺️✈️**
