from app import crud, schemas, database

db = database.SessionLocal()

user = schemas.UserCreate(
    username="admin",
    password="password",
    role="admin"
)

try:
    crud.create_user(db, user)
    print("User 'admin' created with password 'password'")
except Exception as e:
    print(f"Error (maybe user exists): {e}")
finally:
    db.close()
