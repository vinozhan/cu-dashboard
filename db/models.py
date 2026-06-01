from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, index=True)
    project_name = Column(String)
    planning_start_date = Column(Date)
    expiry_date = Column(Date)
    inspection_days = Column(Float, nullable=True)
    inspection_type = Column(String, nullable=True)
    spg_name = Column(String)
    spg_status = Column(String)
    city = Column(String, index=True)
    country = Column(String)
    source_month = Column(String)  # e.g. "Jan 2026"

    def __repr__(self):
        return f"<Audit {self.project_id} - {self.project_name}>"


class ISOProject(Base):
    __tablename__ = "iso_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, index=True)
    project_name = Column(String)
    unit = Column(String, nullable=True)
    address = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    city = Column(String, index=True)
    state = Column(String, nullable=True)
    country = Column(String)
    exp_date = Column(Date)
    iso_standard = Column(String)  # e.g. "ISO 9001", "ISO 14001"

    def __repr__(self):
        return f"<ISOProject {self.project_id} - {self.project_name} ({self.iso_standard})>"


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    code = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FieldDefinition(Base):
    __tablename__ = "field_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_key = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=False)
    data_type = Column(String, nullable=False, default="text")  # text|number|date|boolean
    required = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    file_name = Column(String, nullable=False)
    source_month = Column(String, nullable=True, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)
    status = Column(String, nullable=False, default="completed")  # completed|completed_with_errors|failed


class PlanningRecord(Base):
    __tablename__ = "planning_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    source_month = Column(String, nullable=True, index=True)
    data_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
