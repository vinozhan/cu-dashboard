from sqlalchemy import Column, Integer, String, Date, Float
from sqlalchemy.orm import declarative_base

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
