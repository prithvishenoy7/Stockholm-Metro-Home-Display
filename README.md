# 🚆 Train Departure Display - Backend API

Real-time train departure API for ESP32 LED display, using Trafiklab (SL) data.

## 📚 Learning Objectives

This project teaches:
- **Docker**: Containerization, images vs containers, networking
- **Networking**: REST APIs, HTTP, port mapping, service discovery
- **Security**: Environment variables, secrets management, non-root containers
- **Best Practices**: Caching, rate limiting, health checks

---

## 🏗️ Project Structure

```
backend/
├── app.py              # Flask API with extensive comments
├── Dockerfile          # Container image definition
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── .dockerignore       # Files to exclude from image
```

---

## ⚡ Quick Start

### Prerequisites

1. **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop))
2. **Trafiklab API Key** ([Get one here](https://www.trafiklab.se/api/trafiklab-apis/sl/realtidsinformation-4/))

### Step 1: Create Project Directory

```bash
mkdir train-display
cd train-display
mkdir backend
cd backend
```

### Step 2: Create Files

Copy the provided files into your `backend/` directory:
- `app.py`
- `Dockerfile`
- `requirements.txt`
- `.dockerignore`
- `.env.example`

### Step 3: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual API key
nano .env  # or use your favorite editor
```

Update `.env`:
```bash
TRAFIKLAB_API_KEY=your_actual_api_key_here
DEFAULT_SITE_ID=9192
```

### Step 4: Build and Run

```bash
# Navigate to project root (where docker-compose.yml is)
cd ..

# Build the Docker image and start the container
docker-compose up --build
```

You should see:
```
✅ Building train-api...
✅ Starting train-api...
✅ Running on http://0.0.0.0:5000
```

---

## 🧪 Testing the API

### Test in Browser

Open: `http://localhost:5000`

You should see:
```json
{
  "service": "Train Departure API",
  "status": "running",
  "version": "1.0.0"
}
```

### Get Train Departures

```bash
# Get departures from Stockholm Central (default)
curl http://localhost:5000/departures

# Get departures from a specific station
curl http://localhost:5000/departures/9001  # Slussen
```

### Health Check

```bash
curl http://localhost:5000/health
```

---

## 🐳 Docker Commands Reference

### Basic Operations

```bash
# Start containers in background (detached mode)
docker-compose up -d

# Stop containers
docker-compose down

# View logs (follow mode)
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Restart a service
docker-compose restart api

# Rebuild after code changes
docker-compose up --build
```

### Debugging

```bash
# Execute command inside running container
docker-compose exec api python
docker-compose exec api bash

# View container processes
docker-compose ps

# Inspect container details
docker inspect train-api

# View resource usage
docker stats train-api
```

### Image Management

```bash
# List images
docker images

# Remove unused images
docker image prune

# Remove specific image
docker rmi train-api
```

---

## 🔧 Development Workflow

### Making Changes

1. Edit `app.py` locally
2. Changes auto-reload (volume mounted)
3. Test at `http://localhost:5000`

### Adding Dependencies

1. Add package to `requirements.txt`
2. Rebuild: `docker-compose up --build`

### Environment Variables

Edit `.env` and restart:
```bash
docker-compose restart api
```

---

## 🔍 Understanding Docker Concepts

### Images vs Containers

**Analogy**: Image = Recipe, Container = Baked Cake

```bash
# Build image from Dockerfile (the recipe)
docker build -t train-api ./backend

# Run container from image (bake the cake)
docker run -p 5000:5000 train-api

# One image can create many containers
docker run -p 5001:5000 --name api-instance-1 train-api
docker run -p 5002:5000 --name api-instance-2 train-api
```

### Docker Networking

```
Your Computer                Docker Network (bridge)
┌─────────────┐             ┌──────────────────────┐
│             │             │                      │
│  Browser    │──────────┐  │  ┌──────────────┐    │
│  :5001      │          │  │  │   train-api  │    │
│             │          └──┼──│   :5000      │    │
└─────────────┘             │  └──────────────┘    │
                            │                      │
       Port Mapping         │  ┌──────────────┐    │
       (localhost:5001      │  │   redis      │    │
        → container:5000)   │  │   :6379      │    │
                            │  └──────────────┘    │
                            │                      │
                            │  Containers can talk │
                            │  to each other by    │
                            │  service name!       │
                            └──────────────────────┘
```

**Key Concepts:**
- `0.0.0.0:5000` inside container = listen on all interfaces
- `-p 5000:5000` = map host port 5000 to container port 5000
- Containers on same network use service names (e.g., `http://redis:6379`)

### Docker Volumes

```bash
# Volume Mount: Local directory synced with container
volumes:
  - ./backend:/app  # Changes appear instantly

# Named Volume: Managed by Docker, persists data
volumes:
  - redis-data:/data  # Survives container deletion
```

**Use Cases:**
- Development: Mount code for hot-reload
- Production: Mount logs, persist database data

---

## 🔐 Security Best Practices Implemented

### 1. Non-Root User
```dockerfile
# Don't run as root inside container
RUN useradd -r appuser
USER appuser
```
**Why?** If attacker escapes container, they have limited privileges.

### 2. Environment Variables
```python
# Never hardcode secrets!
API_KEY = os.environ.get('TRAFIKLAB_API_KEY')
```
**Why?** Secrets stay out of code/images, easy to rotate.

### 3. .dockerignore
```
.env
*.key
```
**Why?** Prevents secrets from being baked into images.

### 4. Rate Limiting
```python
@rate_limit(max_calls=30, period=60)
```
**Why?** Prevents abuse, protects against DoS attacks.

### 5. Pinned Dependencies
```
flask==3.0.0  # Not flask>=3.0.0
```
**Why?** Reproducible builds, prevent supply chain attacks.

---

## 🌐 API Endpoints Reference

### `GET /`
Health check and service info
```bash
curl http://localhost:5000/
```

### `GET /departures`
Get departures from default station
```bash
curl http://localhost:5000/departures
```

**Query Parameters:**
- `site_id` - Override default station (optional)

**Response:**
```json
{
  "site_id": "9192",
  "station_name": "Stockholm Central",
  "updated_at": "2025-10-17T10:30:00",
  "departures": [
    {
      "type": "Metro",
      "line": "17",
      "destination": "Åkeshov",
      "display_time": "2 min",
      "expected": "2025-10-17T10:32:00"
    }
  ]
}
```

### `GET /departures/<site_id>`
Get departures for specific station
```bash
curl http://localhost:5000/departures/9001
```

### `POST /cache/clear`
Manually clear cache
```bash
curl -X POST http://localhost:5000/cache/clear
```

---

## 🐛 Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs api
```

**Common issues:**
- Missing API key: Check `.env` file
- Port already in use: Change port in `docker-compose.yml`
- Permission denied: Check file permissions

### API Returns Errors

**Check Trafiklab API key:**
```bash
# Test directly
curl "https://api.sl.se/api2/realtimedeparturesV4.json?key=YOUR_KEY&siteid=9192"
```

**Check container health:**
```bash
docker inspect train-api | grep Health -A 10
```

### Changes Not Reflected

**Volume mount issue:**
```bash
# Rebuild without cache
docker-compose build --no-cache
docker-compose up
```

### Cannot Connect from ESP32

**Check networking:**
```bash
# Find Docker host IP
ifconfig  # Mac/Linux
ipconfig  # Windows

# ESP32 should connect to this IP, not localhost
```

---

## 📈 Next Steps

### Phase 2: Add Redis Caching
- Implement distributed caching
- Learn about multi-container networking
- Practice connecting services

### Phase 3: Deploy to Cloud
- Push image to container registry
- Deploy to AWS/Azure/GCP
- Configure cloud networking

### Phase 4: CI/CD Pipeline
- Automated builds on code push
- Automated testing
- Automated deployment

### Phase 5: Monitoring
- Add Prometheus metrics
- Set up Grafana dashboards
- Implement alerting

---

## 📚 Learning Resources

### Docker
- [Official Docker Docs](https://docs.docker.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### Networking
- [HTTP Protocol Basics](https://developer.mozilla.org/en-US/docs/Web/HTTP)
- [REST API Design](https://restfulapi.net/)

### Security
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Container Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

---

## 🎯 Quiz Yourself

Test your understanding:

1. **What's the difference between an image and a container?**
2. **Why do we use `0.0.0.0` instead of `localhost` in Flask?**
3. **What happens if you delete a container with a volume mount?**
4. **How does rate limiting protect the API?**
5. **Why pin dependency versions?**

---

## 🤝 Contributing

Found an issue or want to improve the code? Feel free to:
1. Fork the repository
2. Make your changes
3. Test thoroughly
4. Submit a pull request

---

## 📝 License

MIT License - Feel free to use for learning and personal projects

---

## 🙏 Acknowledgments

- Trafiklab for providing SL real-time data API
- Docker community for excellent documentation
- Flask team for the lightweight framework