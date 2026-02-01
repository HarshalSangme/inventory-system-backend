# 🚀 Inventory Management System - Backend

FastAPI-based REST API for inventory management system.

## 📋 Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python create_admin.py

# Run server
python -m uvicorn app.main:app --reload

# Open docs
http://localhost:8000/docs
```

### Using Docker

```bash
docker-compose up
```

## 🌐 Deployment Options

### 1️⃣ AWS App Runner (Recommended - 15 min setup)

```bash
python deploy_apprunner.py
```

Or manually:
1. Go to https://console.aws.amazon.com/apprunner/
2. Click "Create service" → "Source code repository"
3. Connect GitHub: `HarshalSangme/inventory-system-backend`
4. Build: `pip install -r requirements.txt`
5. Start: `python create_admin.py && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

**Result**: Public URL in 10-15 minutes  
**Cost**: Free tier available

---

### 2️⃣ Render.com (Easiest - Free tier)

1. Go to https://render.com
2. New → Web Service → Connect GitHub
3. Select `inventory-system-backend`
4. Build: `pip install -r requirements.txt`
5. Start: `python create_admin.py && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
6. Click Deploy

**Result**: Public URL in 5-10 minutes  
**Cost**: FREE (50hr/month free tier)

---

### 3️⃣ Railway.app (Auto-deploy)

1. Go to https://railway.app
2. New Project → Import from GitHub
3. Select `inventory-system-backend`
4. Auto-deploys!

**Result**: Public URL instantly  
**Cost**: $5 free credit/month

---

## 📦 Technology Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **Database**: SQLite (local) / PostgreSQL (production)
- **Auth**: JWT + Passlib + Bcrypt
- **ORM**: SQLAlchemy
- **Container**: Docker

## 🔑 Environment Variables

```bash
DATABASE_URL=sqlite:////tmp/inventory.db  # SQLite
# or
DATABASE_URL=postgresql://user:pass@host/db  # PostgreSQL
```

## 📚 API Endpoints

All endpoints documented at `/docs` (Swagger UI)

### Authentication
- `POST /token` - Login

### Products
- `GET /products` - List all
- `POST /products` - Create
- `PUT /products/{id}` - Update
- `DELETE /products/{id}` - Delete

### Partners  
- `GET /partners` - List all
- `POST /partners` - Create
- `PUT /partners/{id}` - Update
- `DELETE /partners/{id}` - Delete

### Transactions
- `GET /transactions` - List all
- `POST /transactions` - Create
- `PUT /transactions/{id}` - Update
- `DELETE /transactions/{id}` - Delete

## 🔐 Default Credentials

- Username: `admin`
- Password: `admin123`

*Change these in production!*

## 📝 File Structure

```
backend/
├── app/
│   ├── main.py         # FastAPI app, routes
│   ├── models.py       # SQLAlchemy models
│   ├── schemas.py      # Pydantic schemas
│   ├── crud.py         # Database operations
│   ├── database.py     # Database connection
│   ├── auth.py         # JWT authentication
│   └── __pycache__/
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker image
├── docker-compose.yml  # Local development
├── Procfile            # Heroku/Railway deployment
├── render.yaml         # Render.com deployment
├── create_admin.py     # Create admin user
├── populate_data.py    # Seed test data
└── README.md           # This file
```

## 🧪 Testing

```bash
# Create test admin user
python create_admin.py

# Populate sample data
python populate_data.py

# Run tests
pytest tests/
```

## 🐛 Troubleshooting

### Database lock errors
- SQLite uses file locks. For production, use PostgreSQL

### CORS errors  
- CORS is pre-configured for localhost and Amplify domains
- Modify `app/main.py` origins list to add new domains

### Port already in use
```bash
# Use different port
python -m uvicorn app.main:app --port 8001
```

## 📞 Support

- API Docs: http://localhost:8000/docs
- Repo: https://github.com/HarshalSangme/inventory-system-backend
- Issues: Create GitHub issue with details

## 📄 License

MIT
