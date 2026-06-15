from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean
)
from datetime import datetime, timedelta
from database import Base


# =========================
# USERS
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    role = Column(String, default="user")
    password = Column(String)


# =========================
# EQUIPMENT
# =========================
class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    serial_number = Column(String, unique=True, index=True)
    location = Column(String)

    last_calibration_date = Column(
        DateTime,
        default=datetime.utcnow
    )

    calibration_interval_days = Column(
        Integer,
        default=90
    )

    status = Column(
        String,
        default="active"
    )

    owner_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    def get_calibration_status(self):

        if not self.last_calibration_date:
            return "unknown"

        next_due = (
            self.last_calibration_date
            + timedelta(days=self.calibration_interval_days)
        )

        now = datetime.utcnow()

        if now > next_due:
            return "overdue"

        elif (next_due - now).days <= 7:
            return "due_soon"

        return "ok"


# =========================
# MAINTENANCE
# =========================
class Maintenance(Base):
    __tablename__ = "maintenance"

    id = Column(Integer, primary_key=True, index=True)

    equipment_id = Column(
        Integer,
        ForeignKey("equipment.id")
    )

    issue = Column(String)
    action_taken = Column(String)
    performed_by = Column(String)

    status = Column(
        String,
        default="pending"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# =========================
# ALERTS
# =========================
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    equipment_id = Column(
        Integer,
        ForeignKey("equipment.id")
    )

    message = Column(String)

    alert_type = Column(String)
    # calibration
    # maintenance
    # status

    is_resolved = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )