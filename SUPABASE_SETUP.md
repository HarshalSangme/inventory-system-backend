# Production Database Setup - Supabase PostgreSQL

## Quick Overview
This application is configured for production with PostgreSQL. We'll use Supabase for managed PostgreSQL database.

**Total Time:** ~10 minutes  
**Cost:** Free tier available (500MB database, 2GB bandwidth)

---

## Step 1: Create Supabase Project (5 mins)

### 1.1 Sign Up / Login
- Go to: https://supabase.com
- Sign in with GitHub (recommended) or email

### 1.2 Create New Project
- Click **"New Project"**
- **Organization**: Select or create one
- **Name**: `inventory-system` (or your preferred name)
- **Database Password**: Create a strong password (save this!)
- **Region**: Choose closest to your users (e.g., `us-east-1`)
- **Pricing Plan**: Free (or Pro if needed)
- Click **"Create new project"**
- Wait 2-3 minutes for provisioning

---

## Step 2: Get Database Connection String (2 mins)

### 2.1 Navigate to Database Settings
1. In your Supabase project dashboard
2. Click **Settings** (gear icon in sidebar)
3. Click **Database**

### 2.2 Copy Connection String
1. Scroll to **Connection string** section
2. Select **URI** tab (not Nodejs/Python)
3. Copy the connection string (looks like):
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
4. **Important**: Replace `[YOUR-PASSWORD]` with your actual database password

**Connection String Format:**
```
postgresql://postgres.[project-ref]:YourPassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### 2.3 (Alternative) Use Connection Pooler
For production, use **Session mode** connection pooler:
- Port: `6543` (for connection pooling)
- Port: `5432` (for direct connection - less recommended)

---

## Step 3: Configure App Runner (2 mins)

---

## Step 3: Configure App Runner (2 mins)

### 3.1 Add Environment Variable to App Runner
1. Go to **AWS App Runner Console**
2. Select your service
3. Go to **Configuration** → **Environment variables**
4. Click **Add environment variable**
5. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: (Your Supabase connection string from Step 2.2)
6. Click **Save**
7. Wait for automatic redeployment (~5 mins)

---

## Step 4: Deploy Your Application (5 mins)

### 4.1 Build and Push Docker Image
```bash
cd backend

# Build image
docker build -t inventory-backend .

# Tag for ECR
docker tag inventory-backend:latest 388793531822.dkr.ecr.us-east-1.amazonaws.com/inventory-backend:latest

# Authenticate with ECR (if needed)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 388793531822.dkr.ecr.us-east-1.amazonaws.com

# Push to ECR
docker push 388793531822.dkr.ecr.us-east-1.amazonaws.com/inventory-backend:latest
```

### 4.2 Wait for App Runner Auto-Deploy
- App Runner detects new image automatically
- Deployment takes ~5 minutes
- Check logs for successful startup

---

## Step 5: Verify Database Connection (2 mins)

### 5.1 Check App Runner Logs
Look for:
```
No users found, running populate_data.py...
Default admin user created (username: admin, password: admin123)
Database tables created successfully
```

### 5.2 Test API
1. Visit: `https://your-app-runner-url.com/docs`
2. Try `/token` endpoint with:
   - Username: `admin`
   - Password: `admin123`
3. **Change admin password immediately!**

### 5.3 Verify in Supabase
1. Go to Supabase Dashboard
2. Click **Table Editor**
3. You should see tables: `users`, `products`, `partners`, `transactions`, etc.

---

## Supabase Features You Can Use

### Built-in Features:
- **Table Editor**: View/edit data directly in browser
- **SQL Editor**: Run queries
- **Database Backups**: Automatic daily backups (Pro plan)
- **Logs**: Real-time database logs
- **API**: Auto-generated REST and GraphQL APIs (optional)
- **Auth**: Built-in authentication (if you want to migrate from JWT)

### Access Supabase Dashboard:
- Tables: **Table Editor**
- Run SQL: **SQL Editor**  
- Monitoring: **Database** → **Logs**

---

## Security & Best Practices

### ✅ Already Configured:
- Connection pooling (10 connections, max 20)
- Automatic connection recycling (1 hour)
- SSL/TLS enabled by default (Supabase)

### 🔒 Recommended:
1. **Change default admin password** immediately after first login
2. **Enable Row Level Security (RLS)** in Supabase for sensitive tables
3. **Monitor database usage** in Supabase dashboard
4. **Set up alerts** for database limits (free tier: 500MB)

---

## Troubleshooting

### Connection Errors

**Error: "password authentication failed"**
- Check you replaced `[YOUR-PASSWORD]` with actual password
- Verify password is correct in Supabase settings

**Error: "connection refused"**
- Check port: `6543` (pooler) or `5432` (direct)
- Verify connection string format

**Error: "database does not exist"**
- Use `postgres` as database name (default)
- Check connection string ends with `/postgres`

### Check App Runner Logs
```
Service → Logs → Deployment logs
```

### Test Connection from Local
```bash
# Install psql (PostgreSQL client)
# Then test connection:
psql "your-connection-string-here"
```

### Supabase Status
Check: https://status.supabase.com

---

## Connection String Examples

### Standard Format (Connection Pooler - Recommended)
```
postgresql://postgres.abc123xyz:MyPassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Direct Connection (Not Recommended for App Runner)
```
postgresql://postgres.abc123xyz:MyPassword@db.abc123xyz.supabase.co:5432/postgres
```

### With SSL (Supabase enables by default)
```
postgresql://postgres.abc123xyz:MyPassword@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

---

## Cost Information

### Free Tier Includes:
- 500 MB database space
- 2 GB bandwidth per month
- Unlimited API requests
- Daily backups (7 days retention)
- Community support

### Upgrade When Needed:
- Pro: $25/month (8 GB database, more backups)
- Monitor usage in Supabase dashboard

---

## Support

If you encounter issues:
1. Check App Runner logs
2. Check RDS connection from CloudShell or EC2
3. Verify security group rules
4. Test connection string format

---

## What Changed in Your Code

**Modified Files:**
- `database.py` - PostgreSQL support with connection pooling
- `requirements.txt` - Added psycopg2-binary
- `Dockerfile` - PostgreSQL libraries, removed SQLite

**Removed Files:**
- `init_db.py` - Auto-initialization in main.py
- `delete_users.py` - Not needed for production

**Automatic on Startup:**
- Tables created automatically
- Admin user created if none exists
- Sample data populated on first run

---

## Support & Troubleshooting
