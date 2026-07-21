# Docker Setup Guide

This guide explains how to build and run the Booking Room Backend using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose installed (if using docker-compose)
- A `.env` file with all required environment variables

## Files Created

- `Dockerfile` - Main Docker image configuration
- `.dockerignore` - Files to exclude from Docker build context
- `docker-compose.yml` - Docker Compose configuration for easy deployment

## Quick Start with Docker Compose

### 1. Prepare Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set the required values:
- `SECRET_KEY` - Generate a secure random string (min 32 characters)
- `MONGODB_URL` - Your MongoDB connection string
- `BOT_TOKEN` - Your Telegram bot token
- `WEBHOOK_BASE_URL` - Your deployed application URL
- `ADMIN_TELEGRAM_ID` - Your Telegram user ID (numeric)

### 2. Build and Run

```bash
# Build and start the container
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### 3. Access the Application

The API will be available at: `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## Manual Docker Build

If you prefer not to use Docker Compose:

### Build the Image

```bash
docker build -t booking-room-be .
```

### Run the Container

```bash
docker run -d \
  --name booking-room-backend \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  booking-room-be
```

### View Logs

```bash
docker logs -f booking-room-backend
```

### Stop and Remove

```bash
docker stop booking-room-backend
docker rm booking-room-backend
```

## Docker Compose Commands

```bash
# Build and start
docker-compose up --build -d

# Start existing containers
docker-compose start

# Stop containers
docker-compose stop

# Restart containers
docker-compose restart

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f booking-room-be

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes
docker-compose down -v

# Execute command inside container
docker-compose exec booking-room-be bash
```

## Production Considerations

### Security

1. **Environment Variables**: Never commit `.env` files to version control
2. **Non-root User**: The Dockerfile uses a non-root user (`appuser`) for security
3. **Secret Management**: Consider using Docker secrets for sensitive data in production

### Performance

1. **Multi-stage Build**: The current Dockerfile is optimized with slim Python base image
2. **Caching**: Requirements are installed before copying application code for better caching
3. **Health Check**: Built-in health check monitors application status

### Monitoring

The container includes a health check that:
- Runs every 30 seconds
- Checks the `/health` endpoint
- Marks container as unhealthy after 3 failed attempts
- Starts checking 40 seconds after container starts

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs booking-room-be

# Check environment variables
docker-compose config
```

### MongoDB connection issues

- Verify `MONGODB_URL` is correct in `.env`
- Check if MongoDB is accessible from the Docker container
- Ensure MongoDB allows connections from your IP

### Health check failing

```bash
# Check if the app is responding
curl http://localhost:8000/health

# Check container health
docker inspect booking-room-backend | grep -A 10 Health
```

### Permission issues

If you encounter permission issues with mounted volumes, ensure the directory permissions match the container user (UID 1000):

```bash
chown -R 1000:1000 /path/to/volume
```

## Building for Production

For production builds, consider:

1. **Use specific version tags**: Instead of `python:3.11-slim`, use `python:3.11.5-slim`
2. **Optimize image size**: The current setup already uses slim image and cleans up cache
3. **Use build arguments**: Pass environment-specific values at build time:

```dockerfile
ARG APP_ENV=production
ENV APP_ENV=${APP_ENV}
```

Then build with:
```bash
docker build --build-arg APP_ENV=production -t booking-room-be .
```

## Updating the Application

When you make changes to the code:

```bash
# Rebuild and restart
docker-compose up --build -d

# Or just restart if only env vars changed
docker-compose restart
```

## Useful Docker Commands

```bash
# List all containers
docker ps -a

# List all images
docker images

# Remove unused images
docker image prune -a

# Remove unused containers
docker container prune

# View container resource usage
docker stats
```

## CI/CD Integration

The Dockerfile is designed to work with CI/CD pipelines. Example for GitHub Actions:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t booking-room-be .
      - name: Login to Docker Hub
        run: docker login -u ${{ secrets.DOCKER_USERNAME }} -p ${{ secrets.DOCKER_PASSWORD }}
      - name: Push to Docker Hub
        run: docker push yourusername/booking-room-be:latest
```

## Support

For issues specific to Docker deployment, please check:
- Docker logs: `docker-compose logs -f`
- Container status: `docker ps`
- Health check: `docker inspect booking-room-backend`