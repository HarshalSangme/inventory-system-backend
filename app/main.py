from datetime import timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from . import crud, models, schemas, auth, database
import pandas as pd
import io
import random

models.Base.metadata.create_all(bind=database.engine)


app = FastAPI()

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
        print(f"Detected columns: {df.columns.tolist()}")
        
        # Column Mapping
        # DESCRIPTION -> name
        # RATE -> cost_price
        # Retail Price without VAT -> price
        # Order Qty -> stock_quantity
        
        required_columns = ["DESCRIPTION", "RATE", "Retail Price without VAT", "Order Qty"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
             raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing_columns)}. Found: {df.columns.tolist()}")

        imported_count = 0
        
        for index, row in df.iterrows():
            name = row["DESCRIPTION"]
            if pd.isna(name):
                continue
                
            cost_price = pd.to_numeric(row["RATE"], errors='coerce') or 0
            price = pd.to_numeric(row["Retail Price without VAT"], errors='coerce') or 0
            stock_quantity = pd.to_numeric(row["Order Qty"], errors='coerce') or 0
            
            # Generate SKU
            # Try to use SR.NO or SR. NO
            sr_no = row.get("SR.NO") or row.get("SR. NO")
            
            sku = f"SKU-{int(sr_no)}" if sr_no and not pd.isna(sr_no) else f"PROD-{random.randint(1000, 9999)}"
            
            # Check SKU existence
            existing_product = db.query(models.Product).filter(models.Product.sku == sku).first()
            if existing_product:
                 sku = f"{sku}-{random.randint(10, 99)}"
            
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
            
        return {"message": f"Successfully imported {imported_count} products"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")



# Create default admin on startup if not exists
@app.on_event("startup")
async def startup_event():
    db = next(database.get_db())
    try:
        # Ensure default admin exists
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            admin_user = models.User(
                username="admin",
                hashed_password=auth.get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created (username: admin, password: admin123)")
    except Exception as e:
        print(f"Startup initialization error: {e}")
    finally:
        db.close()

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

# Auth Endpoints
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)

# Product Endpoints
@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    products = crud.get_products(db, skip=skip, limit=limit)
    return products

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.create_product(db=db, product=product)

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_active_user)):
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
