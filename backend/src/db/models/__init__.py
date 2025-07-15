from __future__ import annotations
import enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship as SQLModelRelationship
from sqlalchemy.orm import relationship
from sqlalchemy import Column, DateTime, func, TEXT, JSON

from loguru import logger

# --- Enums ---
# These are now standard Python enums, not tied to the database type system.
class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ClashSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

# --- Database Table Models ---

class User(SQLModel, table=True):
    __tablename__ = 'user'
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = Field(default=None)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = Field(default=None, nullable=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False))
    
    reports: List["Report"] = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="user"))

class Report(SQLModel, table=True):
    __tablename__ = 'report'
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, default="Untitled Report")
    acquirer_brand: Optional[str] = Field(default=None)
    target_brand: Optional[str] = Field(default=None)
    status: ReportStatus = Field(default=ReportStatus.DRAFT, sa_column=Column(TEXT, nullable=False))
    extracted_file_context: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    created_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False))
    user_id: int = Field(foreign_key="user.id")

    user: "User" = SQLModelRelationship(sa_relationship=relationship("User", back_populates="reports"))
    analysis: Optional["ReportAnalysis"] = SQLModelRelationship(sa_relationship=relationship("ReportAnalysis", back_populates="report", uselist=False, cascade="all, delete-orphan"))
    culture_clashes: List["CultureClash"] = SQLModelRelationship(sa_relationship=relationship("CultureClash", back_populates="report", cascade="all, delete-orphan"))
    untapped_growths: List["UntappedGrowth"] = SQLModelRelationship(sa_relationship=relationship("UntappedGrowth", back_populates="report", cascade="all, delete-orphan"))

class ReportAnalysis(SQLModel, table=True):
    __tablename__ = 'reportanalysis'
    id: Optional[int] = Field(default=None, primary_key=True)
    cultural_compatibility_score: float = Field(index=True)
    affinity_overlap_score: float
    brand_archetype_summary: str = Field(sa_column=Column(TEXT))
    strategic_summary: str = Field(sa_column=Column(TEXT))
    report_id: int = Field(foreign_key="report.id")
    search_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    acquirer_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    target_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="analysis"))

class CultureClash(SQLModel, table=True):
    __tablename__ = 'cultureclash'
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field(index=True)
    description: str = Field(sa_column=Column(TEXT))
    severity: ClashSeverity = Field(sa_column=Column(TEXT, nullable=False))
    report_id: int = Field(foreign_key="report.id")
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="culture_clashes"))

class UntappedGrowth(SQLModel, table=True):
    __tablename__ = 'untappedgrowth'
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    potential_impact_score: int
    report_id: int = Field(foreign_key="report.id")
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="untapped_growths"))


# --- API Schemas ---
class ReportCreate(SQLModel):
    title: str
    acquirer_brand: str
    target_brand: str

class ReportRead(SQLModel):
    id: int
    title: str
    acquirer_brand: Optional[str]
    target_brand: Optional[str]
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    user_id: int
    analysis: Optional["ReportAnalysis"] = None
    culture_clashes: List[CultureClash] = []
    untapped_growths: List[UntappedGrowth] = []

# DEFINITIVE FIX: Function to resolve all forward references before DB operations.
def rebuild_all_models():
    """
    This function forces the resolution of all forward-looking type hints
    in SQLModel and Pydantic models. It's crucial to call this at startup
    to prevent "type not defined" errors, especially in complex models
    with inter-dependencies.
    """
    logger.info("Rebuilding all model forward references...")
    # Add any other models with forward references here if needed.
    ReportRead.model_rebuild()
    logger.success("Model forward references rebuilt successfully.")

__all__ = [
    "User", "Report", "ReportAnalysis", "CultureClash", "UntappedGrowth",
    "ReportStatus", "ClashSeverity",
    "ReportCreate", "ReportRead",
    "rebuild_all_models"
]