from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Equipment, Maintenance, Alert
from schemas import (
    UserCreate,
    UserLogin,
    UserOut,
    EquipmentCreate,
    EquipmentOut,
    EquipmentStatusUpdate,
    MaintenanceCreate,
    MaintenanceOut,
    CalibrationStatusOut,
    DashboardOut,
    AlertOut,
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    admin_only,
)

router = APIRouter()


# =========================
# SIGNUP
# =========================
@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.name == user.name).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    new_user = User(
        name=user.name,
        role=user.role,
        password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}


# =========================
# LOGIN
# =========================
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(
        User.name == user.name
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials"
        )

    if not verify_password(
        user.password,
        db_user.password
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid credentials"
        )

    token = create_access_token(
        {
            "user_id": db_user.id,
            "role": db_user.role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# =========================
# USERS (ADMIN ONLY)
# =========================
@router.get("/users", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    user=Depends(admin_only),
):
    return db.query(User).all()


# =========================
# MY PROFILE
# =========================
@router.get("/me", response_model=UserOut)
def get_my_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(
        User.id == user["user_id"]
    ).first()

    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return db_user


# =========================
# CREATE EQUIPMENT
# =========================
@router.post("/equipment", response_model=EquipmentOut)
def create_equipment(
    data: EquipmentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment = Equipment(
        name=data.name,
        serial_number=data.serial_number,
        location=data.location,
        status=data.status,
        owner_id=user["user_id"],
    )

    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    return equipment


# =========================
# GET EQUIPMENT
# =========================
@router.get("/equipment", response_model=list[EquipmentOut])
def get_equipment(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return db.query(Equipment).all()


# =========================
# UPDATE EQUIPMENT STATUS
# =========================
@router.patch("/equipment/{equipment_id}/status")
def update_equipment_status(
    equipment_id: int,
    data: EquipmentStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    equipment.status = data.status

    db.commit()
    db.refresh(equipment)

    return equipment


# =========================
# CREATE MAINTENANCE
# =========================
@router.post("/maintenance", response_model=MaintenanceOut)
def create_maintenance(
    data: MaintenanceCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment = db.query(Equipment).filter(
        Equipment.id == data.equipment_id
    ).first()

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    record = Maintenance(
        equipment_id=data.equipment_id,
        issue=data.issue,
        action_taken=data.action_taken,
        performed_by=data.performed_by,
        status=data.status,
    )

    db.add(record)

    issue_text = data.issue.lower()

    if "repair" in issue_text:
        equipment.status = "under_repair"

    if "calibration" in issue_text:
        equipment.status = "calibration_due"

    if data.status == "completed":
        equipment.status = "active"

    db.commit()
    db.refresh(record)

    return record


# =========================
# GET MAINTENANCE
# =========================
@router.get("/maintenance", response_model=list[MaintenanceOut])
def get_maintenance(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return db.query(Maintenance).all()


# =========================
# CALIBRATION STATUS
# =========================
@router.get(
    "/equipment/calibration-status",
    response_model=list[CalibrationStatusOut]
)
def get_calibration_status(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment_list = db.query(Equipment).all()

    result = []

    for eq in equipment_list:
        result.append(
            {
                "id": eq.id,
                "name": eq.name,
                "serial_number": eq.serial_number,
                "location": eq.location,
                "calibration_status": eq.get_calibration_status(),
            }
        )

    return result


# =========================
# GET ALERTS
# =========================
@router.get("/alerts", response_model=list[AlertOut])
def get_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return db.query(Alert).all()


# =========================
# GENERATE ALERTS
# =========================
@router.post("/alerts/generate")
def generate_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment_list = db.query(Equipment).all()

    created = 0

    for eq in equipment_list:

        if eq.status == "calibration_due":
            alert = Alert(
                equipment_id=eq.id,
                message=f"{eq.name} requires calibration",
                alert_type="calibration",
            )

            db.add(alert)
            created += 1

        if eq.status == "under_repair":
            alert = Alert(
                equipment_id=eq.id,
                message=f"{eq.name} is under repair",
                alert_type="maintenance",
            )

            db.add(alert)
            created += 1

    db.commit()

    return {
        "message": "Alerts generated successfully",
        "total_alerts": created,
    }


# =========================
# DASHBOARD
# =========================
@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    equipment = db.query(Equipment).all()
    maintenance = db.query(Maintenance).all()
    alerts = db.query(Alert).all()

    return {
        "total_equipment": len(equipment),
        "active": len(
            [e for e in equipment if e.status == "active"]
        ),
        "under_repair": len(
            [e for e in equipment if e.status == "under_repair"]
        ),
        "calibration_due": len(
            [e for e in equipment if e.status == "calibration_due"]
        ),
        "decommissioned": len(
            [e for e in equipment if e.status == "decommissioned"]
        ),
        "total_maintenance": len(maintenance),
        "total_alerts": len(alerts),
    }