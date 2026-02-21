
from dotenv import load_dotenv
load_dotenv()
from datetime import timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
import threading
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from . import crud, models, schemas, auth, database
from .invoice_pdf import generate_invoice_pdf
from .database import init_database
import pandas as pd
import io
import random
import logging
import time
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from .models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Category Endpoints
@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_categories(db, skip=skip, limit=limit)

@app.post("/categories/", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.create_category(db=db, category=category)

@app.put("/categories/{category_id}", response_model=schemas.Category)
def update_category(category_id: int, category: schemas.CategoryCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_category = crud.update_category(db=db, category_id=category_id, category=category)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    success = crud.delete_category(db=db, category_id=category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"detail": "deleted"}

# --- Email Verification Endpoints ---
from fastapi import BackgroundTasks
import smtplib
from email.mime.text import MIMEText
import secrets

@app.post("/users/{user_id}/send-verification")
def send_verification_email(user_id: int, db: Session = Depends(database.get_db), background_tasks: BackgroundTasks = None, current_user: models.User = Depends(auth.get_current_active_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.email:
        raise HTTPException(status_code=400, detail="User has no email address")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="User already verified")
    from datetime import datetime as dt_now, timedelta
    token = secrets.token_urlsafe(32)
    user.email_verification_token = token
    user.email_verification_token_expiry = dt_now.utcnow() + timedelta(hours=24)
    db.commit()
    def send_email():
        msg = MIMEText(f"Hello {user.username},\n\nPlease verify your email by clicking the link below:\n\nhttps://yourdomain.com/verify-email/{token}\n\nThank you.")
        msg['Subject'] = 'Verify your email'
        msg['From'] = 'noreply@yourdomain.com'
        msg['To'] = user.email
        try:
            pass  # Stub: no actual email sent
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
    if background_tasks:
        background_tasks.add_task(send_email)
    else:
        send_email()
    return {"detail": "Verification email sent (stub)."}

@app.get("/verify-email/{token}")
def verify_email(token: str, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email_verification_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    from datetime import datetime as dt_now
    if not user.email_verification_token_expiry or user.email_verification_token_expiry < dt_now.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_token_expiry = None
    db.commit()
    return {"detail": "Email verified successfully."}



@app.on_event("startup")
async def startup_event():
    # Step 1: Create tables first
    try:
        init_database()
    except Exception as e:
        logger.error(f"CRITICAL: Could not create database tables: {e}")
        logger.error("The application may not work correctly without database tables.")

    # Step 1.5: Migrate — add missing columns to existing tables
    from sqlalchemy import inspect, text
    try:
        insp = inspect(database.engine)
        if insp.has_table("users"):
            existing_cols = {c['name'] for c in insp.get_columns('users')}
            migrations = [
                ('email', 'VARCHAR'),
                ('email_verified', 'BOOLEAN DEFAULT TRUE'),
                ('admin_approved', 'BOOLEAN DEFAULT TRUE'),
                ('email_verification_token', 'VARCHAR'),
                ('email_verification_token_expiry', 'TIMESTAMP'),
            ]
            with database.engine.connect() as conn:
                for col_name, col_type in migrations:
                    if col_name not in existing_cols:
                        conn.execute(text(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}'))
                        conn.commit()
                        logger.info(f"Migration: Added column '{col_name}' to users table")
    except Exception as e:
        logger.error(f"Migration error: {e}")

    # Step 2: Create default admin user
    db = next(database.get_db())
    try:
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            import os
            admin_password = os.getenv("ADMIN_PASSWORD")
            logger.info(f"ADMIN_PASSWORD value: '{admin_password}' (length: {len(admin_password) if admin_password else 'None'})")
            if not admin_password:
                logger.warning("ADMIN_PASSWORD environment variable not set. Using default 'admin123'. Please change this in production!")
                admin_password = "admin123"
            admin_user = models.User(
                username="admin",
                hashed_password=auth.get_password_hash(admin_password),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default admin user created (username: admin)")
        else:
            logger.info("Admin user already exists, skipping creation.")
    except Exception as e:
        logger.error(f"Startup initialization error: {e}")
        db.rollback()
    finally:
        db.close()


@app.post("/import-products/")
async def import_products(file: UploadFile = File(...), db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload an Excel file.")

    try:
        contents = await file.read()
        # Header is on the 3rd row (index 2) based on inspection
        df = pd.read_excel(io.BytesIO(contents), header=2)
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.astype(str).str.strip()
        
        # Print columns for debugging
        logger.info(f"Detected columns: {df.columns.tolist()}")
        
        # Column Mapping
        # DESCRIPTION -> name
        # RATE -> cost_price
        # Retail Price without VAT -> price
        # Order Qty -> stock_quantity
        
        required_columns = ["DESCRIPTION", "AMT (BHD)", "Retail Price without VAT", "Order Qty"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
             raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing_columns)}. Found: {df.columns.tolist()}")

        imported_count = 0
        

        for index, row in df.iterrows():
            name = row["DESCRIPTION"]
            if pd.isna(name):
                continue

            cost_price = pd.to_numeric(row["AMT (BHD)"], errors='coerce')
            price = pd.to_numeric(row["Retail Price without VAT"], errors='coerce')
            stock_quantity = pd.to_numeric(row["Order Qty"], errors='coerce') or 0

            # Strict validation: cost_price and price must be valid numbers
            if pd.isna(cost_price) or pd.isna(price):
                raise HTTPException(status_code=400, detail=f"Invalid or missing cost or retail price at row {index+1}. Please check your Excel file.")

            # Generate SKU
            sr_no = row.get("SR.NO") or row.get("SR. NO")
            base_sku = f"SKU-{int(sr_no)}" if sr_no and not pd.isna(sr_no) else f"PROD-{random.randint(1000, 9999)}"
            sku = base_sku
            counter = 1
            while db.query(models.Product).filter(models.Product.sku == sku).first():
                sku = f"{base_sku}-{counter}"
                counter += 1

            if price < cost_price:
                raise HTTPException(status_code=400, detail=f"Selling price cannot be less than cost price at row {index+1}.")
            product_data = schemas.ProductCreate(
                name=str(name),
                sku=str(sku),
                price=float(price),
                cost_price=float(cost_price),
                stock_quantity=int(stock_quantity),
                min_stock_level=5,
                description="Imported from Excel"
            )
            crud.create_product(db=db, product=product_data)
            imported_count += 1

        db.commit()
        return {"message": f"Successfully imported or updated {imported_count} products"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

origins = [
    "http://localhost:5173",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
    "http://localhost:3000",
    "http://localhost:8000",
    "*",  # Allow all origins for testing
]

# Add Amplify domain regex for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now, restrict after frontend deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware to allow Amplify domains
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import re

class AmplifyCorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        # Allow all amplifyapp.com domains
        if re.match(r"https://.*\.amplifyapp\.com", origin):
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        return await call_next(request)

app.add_middleware(AmplifyCorMiddleware)


# Log failed login attempts
class LoginAttemptLog(Base):
    __tablename__ = "login_attempt_logs"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    success = Column(Boolean, default=False)
    reason = Column(String, nullable=True)

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db), request: Request = None):
    user = crud.get_user_by_username(db, username=form_data.username)
    ip = request.client.host if request and request.client else 'unknown'
    user_agent = request.headers.get("user-agent", "") if request else ''
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        log = LoginAttemptLog(
            username=form_data.username,
            ip_address=ip,
            user_agent=user_agent,
            success=False,
            reason="Invalid credentials"
            
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Block login if not verified/approved (assumes user model has these fields)
    if not getattr(user, 'email_verified', True) or not getattr(user, 'admin_approved', True):
        log = LoginAttemptLog(
            username=form_data.username,
            ip_address=ip,
            user_agent=user_agent,
            success=False,
            reason="Not verified or not approved"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=403, detail="Account not verified or not approved by admin.")
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    log = LoginAttemptLog(
        username=form_data.username,
        ip_address=ip,
        user_agent=user_agent,
        success=True,
        reason="Login success"
    )
    db.add(log)
    db.commit()
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user


# User creation log model (simple inline for now)
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = models.Base  # Use existing Base

class UserCreationLog(Base):
    __tablename__ = "user_creation_logs"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    ip_address = Column(String)
    user_agent = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    success = Column(Boolean, default=False)
    reason = Column(String, nullable=True)

user_creation_attempts = {}
user_creation_lock = threading.Lock()

def check_rate_limit(ip, max_attempts=5, window_seconds=300):
    import time
    now = int(time.time())
    with user_creation_lock:
        attempts = user_creation_attempts.get(ip, [])
        # Remove old attempts
        attempts = [t for t in attempts if now - t < window_seconds]
        if len(attempts) >= max_attempts:
            return False
        attempts.append(now)
        user_creation_attempts[ip] = attempts
    return True

def verify_captcha(captcha_response: str) -> bool:
    # Stub: Integrate with real CAPTCHA provider (e.g., Google reCAPTCHA)
    # For now, always require 'letmein' as the correct answer for testing
    return captcha_response == 'letmein'

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, request: Request, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    ip = request.client.host if request.client else 'unknown'
    # Rate limiting
    if not check_rate_limit(ip):
        log = UserCreationLog(
            username=user.username,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", ""),
            success=False,
            reason="Rate limit exceeded"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")

    # CAPTCHA check disabled for now
    # captcha_response = getattr(user, 'captcha', None)
    # if not captcha_response or not verify_captcha(captcha_response):
    #     log = UserCreationLog(
    #         username=user.username,
    #         ip_address=ip,
    #         user_agent=request.headers.get("user-agent", ""),
    #         success=False,
    #         reason="CAPTCHA failed"
    #     )
    #     db.add(log)
    #     db.commit()
    #     raise HTTPException(status_code=400, detail="CAPTCHA verification failed.")

    # Only admin can create users
    if not current_user or current_user.role != "admin":
        # Log attempt
        log = UserCreationLog(
            username=user.username,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", ""),
            success=False,
            reason="Not authorized"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=403, detail="Only admin can create users")

    # Password policy: min 8 chars, at least 1 digit, 1 uppercase, 1 lowercase
    import re
    password = user.password if hasattr(user, 'password') else None
    if not password or len(password) < 8 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"\d", password):
        log = UserCreationLog(
            username=user.username,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", ""),
            success=False,
            reason="Password policy not met"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters, include uppercase, lowercase, and a digit.")

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        log = UserCreationLog(
            username=user.username,
            ip_address=ip,
            user_agent=request.headers.get("user-agent", ""),
            success=False,
            reason="Username already registered"
        )
        db.add(log)
        db.commit()
        raise HTTPException(status_code=400, detail="Username already registered")

    # Log successful creation
    log = UserCreationLog(
        username=user.username,
        ip_address=ip,
        user_agent=request.headers.get("user-agent", ""),
        success=True,
        reason="Created"
    )
    db.add(log)
    db.commit()
    return crud.create_user(db=db, user=user)



# List all users (admin only)
@app.get("/users/", response_model=List[schemas.User])
def list_users(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(models.User).all()

# Update user details (admin only)
@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    # Update only provided fields
    if user.username is not None:
        db_user.username = user.username
    if user.email is not None and user.email != db_user.email:
        db_user.email = user.email
        # Reset verification when email changes
        db_user.email_verified = False
        db_user.email_verification_token = None
        db_user.email_verification_token_expiry = None
    if user.password:
        db_user.hashed_password = auth.get_password_hash(user.password)
    if user.role is not None:
        db_user.role = user.role
    db.commit()
    db.refresh(db_user)
    return db_user

# Product Endpoints
@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = None, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    products = crud.get_products(db, skip=skip, limit=limit)
    return products

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if product.price < product.cost_price:
        raise HTTPException(status_code=400, detail="Selling price cannot be less than cost price.")
    return crud.create_product(db=db, product=product)

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if product.price < product.cost_price:
        raise HTTPException(status_code=400, detail="Selling price cannot be less than cost price.")
    db_product = crud.update_product(db=db, product_id=product_id, product=product)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    success = crud.delete_product(db=db, product_id=product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"detail": "deleted"}

@app.post("/products/bulk-delete")
def bulk_delete_products(product_ids: List[int], db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    try:
        deleted_count = crud.delete_products_bulk(db=db, product_ids=product_ids)
        return {"message": f"Successfully deleted {deleted_count} product(s)", "deleted_count": deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete products: {str(e)}")

# Partner Endpoints
@app.get("/partners/", response_model=List[schemas.Partner])
def read_partners(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_partners(db, skip=skip, limit=limit)

@app.post("/partners/", response_model=schemas.Partner)
def create_partner(partner: schemas.PartnerCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.create_partner(db=db, partner=partner)


@app.put("/partners/{partner_id}", response_model=schemas.Partner)
def update_partner(partner_id: int, partner: schemas.PartnerCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_partner = crud.update_partner(db=db, partner_id=partner_id, partner=partner)
    if not db_partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    return db_partner


@app.delete("/partners/{partner_id}")
def delete_partner(partner_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    success = crud.delete_partner(db=db, partner_id=partner_id)
    if not success:
        raise HTTPException(status_code=404, detail="Partner not found")
    return {"detail": "deleted"}

# Transaction Endpoints

@app.get("/transactions/", response_model=List[schemas.Transaction])
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_transactions(db, skip=skip, limit=limit)

@app.put("/transactions/{transaction_id}", response_model=schemas.Transaction)
def update_transaction(transaction_id: int, transaction: schemas.TransactionCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_transaction = crud.update_transaction(db, transaction_id, transaction)
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_transaction

@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    success = crud.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"detail": "deleted"}

@app.post("/transactions/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    try:
        # Always set sales_person from the logged-in user
        transaction_data = transaction.dict()
        transaction_data["sales_person"] = current_user.username
        return crud.create_transaction(db=db, transaction=schemas.TransactionCreate(**transaction_data))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch other unexpected errors
        print(f"Error creating transaction: {e}") 
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/dashboard")
def get_dashboard(db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_dashboard_stats(db)

# Invoice PDF Generation
class InvoiceEditData(BaseModel):
    invoice_number: str
    payment_terms: str = "CREDIT"
    due_date: Optional[str] = None
    sales_person: str = ""  # Dynamic - comes from transaction's logged-in user

@app.post("/transactions/{transaction_id}/invoice")
def generate_invoice(
    transaction_id: int,
    edit_data: InvoiceEditData,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    # Get transaction with related data
    transaction = db.query(models.Transaction).options(
        joinedload(models.Transaction.partner),
        joinedload(models.Transaction.items).joinedload(models.TransactionItem.product)
    ).filter(models.Transaction.id == transaction_id).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Convert to dict for PDF generator
    invoice_data = {
        'id': transaction.id,
        'date': transaction.date.isoformat() if transaction.date else None,
        'type': transaction.type,
        'total_amount': float(transaction.total_amount) if transaction.total_amount else 0,
        'vat_percent': float(transaction.vat_percent) if transaction.vat_percent else 0,
        'partner': {
            'name': transaction.partner.name if transaction.partner else '',
            'address': transaction.partner.address if transaction.partner else '',
            'phone': transaction.partner.phone if transaction.partner else '',
        } if transaction.partner else {},
        'items': [
            {
                'product': {
                    'name': item.product.name if item.product else '',
                    'sku': item.product.sku if item.product else '',
                },
                'quantity': item.quantity,
                'price': float(item.price) if item.price else 0,
                'discount': float(item.discount) if item.discount else 0,
            }
            for item in transaction.items
        ],
        'sales_person': transaction.sales_person or edit_data.sales_person,
    }
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(invoice_data, edit_data.dict())
    
    # Return as streaming response
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=invoice_{edit_data.invoice_number.replace('/', '_')}.pdf"
        }
    )

@app.get("/transactions/{transaction_id}/invoice/pdf")
def get_invoice_pdf(
    transaction_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Directly generate PDF for printing with default/existing invoice number.
    If no invoice number exists, one is generated temporarilly or fetched if stored.
    Currently we don't store invoice number in DB, so we generate a default one: JOT/{YEAR}/{ID}
    """
    # Get transaction with related data
    transaction = db.query(models.Transaction).options(
        joinedload(models.Transaction.partner),
        joinedload(models.Transaction.items).joinedload(models.TransactionItem.product)
    ).filter(models.Transaction.id == transaction_id).first()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    # Generate default invoice number
    # Format: JOT/YYYY/ID (padded to 3 digits)
    year = transaction.date.year
    invoice_number = f"JOT/{year}/{transaction.id:03d}"
    
    # Check if we should use different fields
    payment_terms = "CREDIT" # Default
    due_date = None # Default
    
    # Prepare edit data with defaults
    edit_data = {
        "invoice_number": invoice_number,
        "payment_terms": payment_terms,
        "due_date": due_date,
        "sales_person": transaction.sales_person or ""
    }
    
    # Prepare details for PDF generator
    invoice_data = {
        'id': transaction.id,
        'date': transaction.date.isoformat() if transaction.date else None,
        'type': transaction.type,
        'total_amount': float(transaction.total_amount) if transaction.total_amount else 0,
        'vat_percent': float(transaction.vat_percent) if transaction.vat_percent else 0,
        'partner': {
            'name': transaction.partner.name if transaction.partner else '',
            'address': transaction.partner.address if transaction.partner else '',
            'phone': transaction.partner.phone if transaction.partner else '',
        } if transaction.partner else {},
        'items': [
            {
                'product': {
                    'name': item.product.name if item.product else '',
                    'sku': item.product.sku if item.product else '',
                },
                'quantity': item.quantity,
                'price': float(item.price) if item.price else 0,
                'discount': float(item.discount) if item.discount else 0,
            }
            for item in transaction.items
        ],
        'sales_person': transaction.sales_person or "",
    }
    
    # Generate PDF
    pdf_buffer = generate_invoice_pdf(invoice_data, edit_data)
    
    # Return as streaming response - inline for browser viewing
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=invoice_{invoice_number.replace('/', '_')}.pdf"
        }
    )
