from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

import models
import schemas
from database import SessionLocal, engine, Base

app = FastAPI()

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DATABASE
# =========================

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "message": "Complisure Backend is running 🚀",
        "status": "active"
    }

# =========================
# AUTH
# =========================

SECRET_KEY = "supersecretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return email

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

# =========================
# USERS
# =========================

@app.post("/users", response_model=schemas.UserOut)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):

    existing = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    db_user = models.User(
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()


@app.get("/users/me")
def get_me(user: str = Depends(get_current_user)):
    return {"email": user}

# =========================
# LOGIN
# =========================

@app.post("/login")
def login(
    user: schemas.UserLogin,
    db: Session = Depends(get_db)
):

    db_user = db.query(models.User).filter(
        models.User.email == user.email
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        user.password,
        db_user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_token(
        {"sub": db_user.email}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role
        }
    }

# =========================
# EQUIPMENT
# =========================

@app.post("/equipment")
def create_equipment(
    equipment: schemas.EquipmentCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    item = models.Equipment(**equipment.dict())

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@app.get("/equipment")
def get_equipment(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    return db.query(models.Equipment).all()


@app.get("/equipment/{equipment_id}")
def get_one(
    equipment_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    item = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return item


@app.put("/equipment/{equipment_id}")
def update_equipment(
    equipment_id: int,
    equipment: schemas.EquipmentCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    item = db.query(models.Equipment).filter(
        models.Equipment.id == equipment_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    for key, value in equipment.dict().items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

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
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Equipment deleted successfully"
    }

# =========================
# DASHBOARD
# =========================

@app.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):

    total = db.query(models.Equipment).count()

    active = db.query(models.Equipment).filter(
        models.Equipment.status == "active"
    ).count()

    repair = db.query(models.Equipment).filter(
        models.Equipment.status == "repair"
    ).count()

    return {
        "total": total,
        "active": active,
        "repair": repair,
        "inactive": total - active
    }