# StringDB-Link Docker Deployment

Production-ready Docker setup for StringDB-Link with multi-stage builds and optimized configurations.

## 🚀 Quick Start

### Development Setup

```bash
# Copy environment template (if not already done)
cp .env.example .env

# Build and run development server
cd docker
docker-compose up --build
```

Server available at `http://localhost:8000` with API docs at `/docs`.

### Production Deployment

```bash
# Build and run production server
cd docker
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📁 File Structure

```
docker/
├── Dockerfile                 # Multi-stage production build
├── docker-compose.yml         # Development configuration
├── docker-compose.prod.yml    # Production overrides
├── docker-compose.dev.yml     # Hot-reload development (optional)
├── docker-compose.npm.yml     # NPM production deployment
├── gunicorn_conf.py          # Production WSGI configuration
├── .dockerignore             # Build optimization
└── README.md                 # This file

# Environment files (in project root)
├── .env.example              # Local development template
└── .env.npm.example          # NPM production template
```

## 🔧 Configuration

Key environment variables (edit `.env`):

```env
# Server settings
STRINGDB_LINK_HOST=127.0.0.1
STRINGDB_LINK_PORT=8000
STRINGDB_LINK_LOG_LEVEL=INFO
ALLOWED_HOSTS=["localhost","127.0.0.1","::1"]
ALLOWED_ORIGINS=[]

# CORS settings (JSON format required)
STRINGDB_LINK_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
STRINGDB_LINK_CORS_ALLOW_METHODS=["GET","POST","PUT","DELETE","OPTIONS"]
STRINGDB_LINK_CORS_ALLOW_HEADERS=["*"]

# Production scaling
GUNICORN_WORKERS=4
GUNICORN_THREADS=4
```

## 🏗️ Architecture

**Multi-Stage Build:**
- **Builder**: Installs dependencies in virtual environment
- **Production**: Minimal runtime image with non-root user

**Development vs Production:**
- Development: Simple uvicorn server, debug logging
- Production: Gunicorn + Uvicorn workers, JSON logging, resource limits

## 🐳 Deployment Options

### Local Development
```bash
docker-compose up --build
```

### Hot-Reload Development (optional)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Production (Local Server)
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### NPM Production Deployment
```bash
# Setup NPM environment
cp .env.npm.example .env.npm
# Edit .env.npm with your domain and settings

# Deploy with NPM configuration
docker-compose -f docker-compose.yml -f docker-compose.npm.yml up -d
```

### Container Registry
```bash
# Build and push
docker build -f Dockerfile -t your-registry/stringdb-link:latest ..
docker push your-registry/stringdb-link:latest

# Run from registry
docker run -d --name stringdb-link -p 8000:8000 --env-file ../.env your-registry/stringdb-link:latest
```

## 🌐 Nginx Proxy Manager (NPM) Integration

StringDB-Link includes built-in support for deployment with Nginx Proxy Manager for production hosting with custom domains and SSL certificates.

### NPM Prerequisites

1. **Running NPM Instance**: Nginx Proxy Manager should be running on your server
2. **Shared Network**: Verify NPM's Docker network name with `docker network ls` (typically `npm_default`)
3. **Domain Access**: DNS records pointing your domain to the server

### NPM Setup Process

#### 1. Environment Configuration
```bash
# Copy and customize NPM environment
cp .env.npm.example .env.npm

# Edit .env.npm with your settings:
# - NPM_SHARED_NETWORK_NAME=npm_default (or your NPM network)
# - STRINGDB_LINK_PUBLIC_DOMAIN=stringdb.yourdomain.com
# - STRINGDB_LINK_CORS_ORIGINS=["https://stringdb.yourdomain.com"]
```

#### 2. Deploy StringDB-Link
```bash
# Deploy container without direct port exposure
docker-compose -f docker-compose.yml -f docker-compose.npm.yml up -d
```

#### 3. Configure NPM Proxy Host
In your NPM web interface:
- **Domain Names**: `stringdb.yourdomain.com`
- **Scheme**: `http`
- **Forward Hostname/IP**: `stringdb-link` (container name)
- **Forward Port**: `8000`
- **Enable SSL**: Add/Request SSL certificate

#### 4. Verify Deployment
```bash
# Check container health
docker-compose logs stringdb-link

# Test health endpoint through NPM
curl https://stringdb.yourdomain.com/api/health
```

### NPM Network Architecture

```
Internet → NPM (SSL/443) → Docker Network → StringDB-Link Container (8000)
```

- **External Access**: Through your domain with SSL
- **Internal Routing**: NPM forwards to `stringdb-link:8000`
- **No Direct Ports**: Container doesn't expose ports on host
- **Network Isolation**: Services communicate via shared Docker network

### NPM Configuration Examples

#### Basic Proxy Host
- **Domain**: `stringdb.yourdomain.com`
- **Destination**: `stringdb-link:8000`
- **SSL**: Let's Encrypt or custom certificate

#### Advanced Configuration
- **Custom locations**: `/api/*` for API-specific routing
- **Caching**: Enable for static assets if needed
- **Rate limiting**: Configure in NPM for additional protection
- **Access lists**: Restrict access by IP if required

### NPM vs Development Differences

| Feature | Development | NPM Production |
|---------|-------------|----------------|
| **Access** | `localhost:8000` | `https://yourdomain.com` |
| **Ports** | Direct port mapping | No port exposure |
| **SSL** | None | NPM-managed SSL |
| **Networks** | Bridge only | NPM shared network |
| **Logging** | Console format | JSON format |
| **CORS** | Localhost origins | Production domains |

## 🔍 Monitoring

- **Health Check**: `curl http://localhost:8000/api/health`
- **API Documentation**: `http://localhost:8000/docs`
- **Container Logs**: `docker-compose logs -f stringdb-link`

## 🛠️ Development Workflow

1. Edit source code in `../stringdb_link/`
2. For simple changes: `docker-compose restart stringdb-link`
3. For dependency changes: `docker-compose up --build`

## 🚨 Troubleshooting

**Port conflicts:**
```bash
# Change port in .env
STRINGDB_LINK_PORT=8001
```

**Permission errors:**
```bash
# Clean build cache
docker system prune -a
docker-compose build --no-cache
```

**CORS configuration:**
- Must use JSON array format in environment variables
- Example: `["http://localhost:3000","http://localhost:8080"]`

**NPM deployment issues:**
```bash
# Check if NPM network exists
docker network ls | grep npm

# Verify container is on NPM network
docker inspect stringdb-link | grep NetworkMode

# Check NPM container logs
docker logs nginx-proxy-manager

# Test internal connectivity
docker exec stringdb-link curl -f http://localhost:8000/api/health
```

**NPM proxy configuration:**
- Ensure Forward Hostname/IP is `stringdb-link` (not IP address)
- Use scheme `http` (not https) for internal routing
- Forward Port should be `8000`
- SSL should be configured in NPM, not the container

## 🔐 Security Features

- Non-root container user (`app:app`)
- Minimal base image (Python 3.11 slim)
- No secrets in image layers
- Resource limits and health checks
- Production-grade process management

## 🖥️ VPS Production Deployment Guide

Complete guide for deploying StringDB-Link on a Virtual Private Server with Nginx Proxy Manager.

### Prerequisites

1. **VPS Requirements**:
   - Ubuntu 20.04+ or similar Linux distribution
   - 2GB+ RAM, 1+ CPU cores
   - 20GB+ storage space
   - Root or sudo access

2. **Domain Setup**:
   - Domain name pointing to your VPS IP
   - DNS A record configured (e.g., `stringdb.yourdomain.com` → `your.vps.ip`)

3. **NPM Installation**:
   - Nginx Proxy Manager running on the same VPS
   - NPM accessible via web interface (typically port 81)

### Step-by-Step Deployment

#### 1. Server Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose git

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (logout/login required)
sudo usermod -aG docker $USER
```

#### 2. Project Setup

```bash
# Clone the repository
git clone https://github.com/your-org/stringdb-link.git
cd stringdb-link

# Create production environment file
cp .env.npm.example .env.npm

# Edit environment with your domain settings
nano .env.npm
```

#### 3. Environment Configuration

Edit `.env.npm` with your specific settings:

```env
# Critical settings to customize:
NPM_SHARED_NETWORK_NAME=npm_default
STRINGDB_LINK_PUBLIC_DOMAIN=stringdb.yourdomain.com  
STRINGDB_LINK_PUBLIC_URL=https://stringdb.yourdomain.com
STRINGDB_LINK_CORS_ORIGINS=["https://stringdb.yourdomain.com"]

# Production optimizations:
GUNICORN_WORKERS=4
GUNICORN_LOG_LEVEL=warning
STRINGDB_LINK_LOG_LEVEL=INFO
```

#### 4. Network Verification

```bash
# Verify NPM network exists
docker network ls | grep npm

# If NPM network doesn't exist, check NPM container
docker ps | grep nginx-proxy-manager

# Get actual network name if different
docker inspect <npm_container_id> | grep NetworkMode
```

#### 5. Deploy StringDB-Link

```bash
# Build and deploy with NPM configuration
cd docker
docker-compose -f docker-compose.yml -f docker-compose.npm.yml up -d --build

# Verify deployment
docker-compose logs -f stringdb-link
```

#### 6. NPM Proxy Configuration

1. **Access NPM Web Interface**:
   - Open `http://your-vps-ip:81`
   - Login with your NPM credentials

2. **Create Proxy Host**:
   - **Domain Names**: `stringdb.yourdomain.com`
   - **Scheme**: `http` (internal)
   - **Forward Hostname/IP**: `stringdb-link`
   - **Forward Port**: `8000`
   - **Cache Assets**: Enable
   - **Block Common Exploits**: Enable

3. **Configure SSL**:
   - Go to SSL tab
   - Select "Request a new SSL Certificate"
   - Enable "Force SSL" and "HTTP/2 Support"
   - Add email for Let's Encrypt

#### 7. Verification and Testing

```bash
# Check container health
docker exec stringdb-link curl -f http://localhost:8000/api/health

# Test external access
curl https://stringdb.yourdomain.com/api/health

# Check logs
docker-compose -f docker-compose.yml -f docker-compose.npm.yml logs stringdb-link
```

### Production Monitoring

#### Log Management

```bash
# View real-time logs
docker-compose -f docker-compose.yml -f docker-compose.npm.yml logs -f stringdb-link

# View specific time range
docker-compose logs --since=1h stringdb-link

# Check log file sizes (automatic rotation configured)
docker exec stringdb-link ls -la /var/log/
```

#### Health Monitoring

```bash
# Create health check script
cat > /opt/stringdb-health-check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="https://stringdb.yourdomain.com/api/health"
if curl -f -s "$HEALTH_URL" > /dev/null; then
    echo "$(date): StringDB-Link is healthy"
else
    echo "$(date): StringDB-Link health check failed" >&2
    # Optional: restart container
    # docker-compose -f /path/to/docker-compose.yml restart stringdb-link
fi
EOF

chmod +x /opt/stringdb-health-check.sh

# Add to crontab for periodic checking
(crontab -l ; echo "*/5 * * * * /opt/stringdb-health-check.sh >> /var/log/stringdb-health.log") | crontab -
```

#### Resource Monitoring

```bash
# Monitor container resources
docker stats stringdb-link

# Check disk usage
docker system df

# Monitor logs size
docker-compose config | grep max-size
```

### Maintenance and Updates

#### Update Deployment

```bash
# Pull latest changes
git pull origin main

# Rebuild and redeploy
docker-compose -f docker-compose.yml -f docker-compose.npm.yml down
docker-compose -f docker-compose.yml -f docker-compose.npm.yml up -d --build

# Verify health
curl https://stringdb.yourdomain.com/api/health
```

#### Backup Configuration

```bash
# Backup environment and configs
tar -czf stringdb-backup-$(date +%Y%m%d).tar.gz .env.npm docker/

# Backup to remote location (optional)
scp stringdb-backup-*.tar.gz user@backup-server:/backups/
```

### Troubleshooting VPS Deployment

#### Common Issues

**Container won't start:**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check container logs
docker-compose logs stringdb-link

# Verify environment file
cat .env.npm | grep -v "^#" | grep -v "^$"
```

**NPM connectivity issues:**
```bash
# Verify network connectivity
docker exec stringdb-link ping npm-container-name

# Check network attachments
docker inspect stringdb-link | grep -A 10 Networks

# Test internal health endpoint
docker exec stringdb-link curl localhost:8000/api/health
```

**SSL certificate issues:**
```bash
# Check NPM logs
docker logs nginx-proxy-manager

# Verify domain DNS
nslookup stringdb.yourdomain.com

# Test port 80/443 accessibility
curl -I http://stringdb.yourdomain.com
```

**Performance issues:**
```bash
# Monitor resource usage
htop
docker stats

# Check STRING API rate limits
docker-compose logs stringdb-link | grep -i rate

# Adjust worker count in .env.npm
# GUNICORN_WORKERS=2  # For lower-spec VPS
```

### Security Hardening

#### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 81/tcp  # NPM admin (consider restricting by IP)
sudo ufw enable
```

#### Regular Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Docker updates
sudo apt update docker.io docker-compose

# Container updates (schedule monthly)
docker-compose pull && docker-compose up -d
```

## 🎯 StringDB-Link Specific Features

### MCP Integration
StringDB-Link provides both REST API and MCP (Model Context Protocol) interfaces:

```bash
# Start unified server (HTTP + MCP)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
# Server provides both REST API and MCP endpoints
```

### STRING Database Features
The containerized application provides access to:
- Protein-protein interaction networks
- Functional enrichment analysis
- Homology mapping
- Protein annotations
- Network visualization

### Health Checks
StringDB-Link includes comprehensive health monitoring:
- Container health checks
- API endpoint monitoring
- STRING database connectivity verification
- Resource usage tracking

This comprehensive VPS deployment guide provides everything needed to run StringDB-Link in production with NPM on a virtual private server.
