from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# =========================
# USER SCHEMAS
# =========================

class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


# =========================
# EQUIPMENT SCHEMAS
# =========================

class EquipmentCreate(BaseModel):
    name: str
    serial_number: str
    location: str
    status: str = "active"


class EquipmentOut(BaseModel):
    id: int
    name: str
    serial_number: str
    location: str
    status: str
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True


class EquipmentStatusUpdate(BaseModel):
    status: str


# =========================
# MAINTENANCE SCHEMAS
# =========================

class MaintenanceCreate(BaseModel):
    equipment_id: int
    issue: str
    action_taken: str
    performed_by: str
    status: str = "pending"


class MaintenanceOut(BaseModel):
    id: int
    equipment_id: int
    issue: str
    action_taken: str
    performed_by: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# CALIBRATION SCHEMAS
# =========================

class CalibrationStatusOut(BaseModel):
    id: int
    name: str
    serial_number: str
    location: str
    calibration_status: str

    class Config:
        from_attributes = True


# =========================
# ALERT SCHEMAS
# =========================

class AlertOut(BaseModel):
    id: int
    equipment_id: int
    message: str
    alert_type: str
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# DASHBOARD SCHEMAS
# =========================

class DashboardOut(BaseModel):
    total_equipment: int
    active: int
    under_repair: int
    calibration_due: int
    decommissioned: int
    total_maintenance: int
    total_alerts: int