from __future__ import annotations
import enum
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship as SQLModelRelationship
from sqlalchemy.orm import relationship
from sqlalchemy import Column, DateTime, Enum as SAEnum, func, TEXT
from loguru import logger

# --- Enums ---
class ReportStatus(str, enum.Enum):
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
    title: str = Field(index=True)
    acquirer_brand: str
    target_brand: str
    status: ReportStatus = Field(sa_column=Column(SAEnum(ReportStatus), nullable=False), default=ReportStatus.PENDING)
    # --- FIX: Mark server-defaulted columns as Optional in the model ---
    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )
    user_id: int = Field(foreign_key="user.id")

    # --- Relationships ---
    user: "User" = SQLModelRelationship(sa_relationship=relationship("User", back_populates="reports"))
    analysis: Optional["ReportAnalysis"] = SQLModelRelationship(sa_relationship=relationship("ReportAnalysis", back_populates="report", uselist=False))
    culture_clashes: List["CultureClash"] = SQLModelRelationship(sa_relationship=relationship("CultureClash", back_populates="report"))
    untapped_growths: List["UntappedGrowth"] = SQLModelRelationship(sa_relationship=relationship("UntappedGrowth", back_populates="report"))

class ReportAnalysis(SQLModel, table=True):
    __tablename__ = 'reportanalysis'
    id: Optional[int] = Field(default=None, primary_key=True)
    cultural_compatibility_score: float = Field(index=True)
    affinity_overlap_score: float
    brand_archetype_summary: str = Field(sa_column=Column(TEXT))
    strategic_summary: str = Field(sa_column=Column(TEXT))
    report_id: int = Field(foreign_key="report.id")
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="analysis"))

class CultureClash(SQLModel, table=True):
    __tablename__ = 'cultureclash'
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field(index=True)
    description: str = Field(sa_column=Column(TEXT))
    severity: ClashSeverity = Field(sa_column=Column(SAEnum(ClashSeverity)))
    report_id: int = Field(foreign_key="report.id")
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="culture_clashes"))

class UntappedGrowth(SQLModel, table=True):
    __tablename__ = 'untappedgrowth'
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    potential_impact_score: int
    report_id: int = Field(foreign_key="report.id")
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="untapped_growths"))

# --- API Schemas (for request/response validation) ---
class ReportCreate(SQLModel):
    title: str
    acquirer_brand: str
    target_brand: str

class ReportRead(SQLModel):
    id: int
    title: str
    acquirer_brand: str
    target_brand: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    user_id: int
    analysis: Optional[ReportAnalysis] = None
    culture_clashes: List[CultureClash] = []
    untapped_growths: List[UntappedGrowth] = []

# --- Lifespan Helper ---
def rebuild_all_models():
    """Forces SQLModel/Pydantic to resolve all string-based forward references."""
    logger.info("Rebuilding all model forward references...")
    ReportRead.model_rebuild()
    logger.success("Model forward references rebuilt successfully.")

__all__ = [
    "User", "Report", "ReportAnalysis", "CultureClash", "UntappedGrowth",
    "ReportStatus", "ClashSeverity",
    "ReportCreate", "ReportRead",
    "rebuild_all_models"
]