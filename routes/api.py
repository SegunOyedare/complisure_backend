from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Equipment, Maintenance, Alert
from schemas import (
    UserCreate,
    UserLogin,
    EquipmentCreate,
    EquipmentStatusUpdate,
    MaintenanceCreate,
    EquipmentOut,
    MaintenanceOut,
    AlertOut
)

from passlib.context import CryptContext

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# PASSWORD HELPERS
# =========================
def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# =========================
# SIGNUP
# =========================
@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "role": new_user.role
        }
    }


# =========================
# LOGIN
# =========================
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    return {
        "message": "Login successful 🚀",
        "user": {
            "id": db_user.id,
            "email": db_user.email,
            "role": db_user.role
        }
    }


# =========================
# EQUIPMENT
# =========================

@router.get("/equipment", response_model=list[EquipmentOut])
def get_equipment(db: Session = Depends(get_db)):
    return db.query(Equipment).all()


@router.post("/equipment", response_model=EquipmentOut)
def create_equipment(data: EquipmentCreate, db: Session = Depends(get_db)):

    equipment = Equipment(**data.dict())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    return equipment


@router.patch("/equipment/{equipment_id}/status")
def update_equipment_status(
    equipment_id: int,
    data: EquipmentStatusUpdate,
    db: Session = Depends(get_db)
):

    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()

    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    equipment.status = data.status
    db.commit()

    return {"message": "Equipment status updated"}


# =========================
# MAINTENANCE
# =========================

@router.get("/maintenance", response_model=list[MaintenanceOut])
def get_maintenance(db: Session = Depends(get_db)):
    return db.query(Maintenance).all()


@router.post("/maintenance", response_model=MaintenanceOut)
def create_maintenance(data: MaintenanceCreate, db: Session = Depends(get_db)):

    maintenance = Maintenance(**data.dict())
    db.add(maintenance)
    db.commit()
    db.refresh(maintenance)

    return maintenance


# =========================
# ALERTS
# =========================

@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).all()


@router.post("/alerts/generate")
def generate_alerts(db: Session = Depends(get_db)):

    faulty = db.query(Equipment).filter(Equipment.status != "active").all()

    return {
        "message": "Alerts generated",
        "count": len(faulty)
    }


# =========================
# CALIBRATION STATUS
# =========================

@router.get("/equipment/calibration-status")
def calibration_status(db: Session = Depends(get_db)):

    equipment = db.query(Equipment).all()

    return [
        {
            "id": e.id,
            "name": e.name,
            "serial_number": e.serial_number,
            "location": e.location,
            "calibration_status": "due" if e.status != "active" else "ok"
        }
        for e in equipment
    ]


# =========================
# DASHBOARD
# =========================

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):

    return {
        "total_equipment": db.query(Equipment).count(),
        "active": db.query(Equipment).filter(Equipment.status == "active").count(),
        "under_repair": db.query(Equipment).filter(Equipment.status == "repair").count(),
        "calibration_due": db.query(Equipment).filter(Equipment.status != "active").count(),
        "decommissioned": 0,
        "total_maintenance": db.query(Maintenance).count(),
        "total_alerts": db.query(Alert).count()
    }


# =========================
# HOME
# =========================
@router.get("/")
def home():
    return {"message": "Complisure API is running 🚀"}