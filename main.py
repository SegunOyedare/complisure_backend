from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal, engine, Base

# =========================
# AUTH IMPORTS
# =========================
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta

app = FastAPI()

# =========================
# ROOT TEST (DEPLOY CHECK)
# =========================
@app.get("/")
def root():
    return {"message": "Complisure API is running 🚀"}

# =========================
# CREATE TABLES (SQLite)
# =========================
Base.metadata.create_all(bind=engine)

# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# AUTH CONFIG
# =========================
SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# =========================
# PASSWORD HELPERS
# =========================
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# GET CURRENT USER
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        return email

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# =========================================================
# 👤 USERS
# =========================================================

@app.post("/users", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):

    db_user = models.User(
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.get("/users", response_model=list[schemas.UserOut])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# =========================================================
# 🔐 LOGIN
# =========================================================

@app.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": db_user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role
        }
    }

# =========================================================
# 📦 EQUIPMENT (PROTECTED)
# =========================================================

@app.post("/equipment", response_model=schemas.EquipmentOut)
def create_equipment(
    equipment: schemas.EquipmentCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    new_item = models.Equipment(
        name=equipment.name,
        serial_number=equipment.serial_number,
        location=equipment.location,
        status=equipment.status
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return new_item


@app.get("/equipment", response_model=list[schemas.EquipmentOut])
def get_equipment(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    return db.query(models.Equipment).all()


@app.get("/equipment/{equipment_id}", response_model=schemas.EquipmentOut)
def get_single_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    item = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")

    return item


@app.delete("/equipment/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    item = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")

    db.delete(item)
    db.commit()

    return {"message": "Equipment deleted successfully"}

# =========================================================
# 📊 DASHBOARD STATS (PROTECTED)
# =========================================================

@app.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    total = db.query(models.Equipment).count()

    active = db.query(models.Equipment).filter(
        models.Equipment.status == "active"
    ).count()

    under_repair = db.query(models.Equipment).filter(
        models.Equipment.status == "repair"
    ).count()

    return {
        "total_equipment": total,
        "active": active,
        "under_repair": under_repair,
        "inactive": total - active
    }

# =========================================================
# RUN SERVER (LOCAL ONLY)
# =========================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)