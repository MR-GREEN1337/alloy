from __future__ import annotations
import enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone 
import uuid 
from sqlmodel import Field, SQLModel, Relationship as SQLModelRelationship
from sqlalchemy.orm import relationship
from sqlalchemy import Column, DateTime, func, TEXT, JSON, ForeignKey # Import ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from loguru import logger

# --- Enums ---
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    # THE FIX: Make updated_at non-optional and provide a default_factory
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )
    
    reports: List["Report"] = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="user"))

class Report(SQLModel, table=True):
    __tablename__ = 'report'
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            index=True,
            nullable=False
        )
    )
    title: str = Field(index=True, default="Untitled Report")
    acquirer_brand: Optional[str] = Field(default=None)
    target_brand: Optional[str] = Field(default=None)
    status: ReportStatus = Field(default=ReportStatus.DRAFT, sa_column=Column(TEXT, nullable=False))
    extracted_file_context: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    # THE FIX: Make updated_at non-optional and provide a default_factory
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )
    # Note: user_id still references the integer PK of the User table
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
    # THE FIX: Mark all LLM-generated text fields as Optional to handle generation failures.
    brand_archetype_summary: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    strategic_summary: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    report_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("report.id")))
    search_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    acquirer_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    target_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    # Corporate culture fields
    acquirer_corporate_profile: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    target_corporate_profile: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    corporate_ethos_summary: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    acquirer_culture_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    target_culture_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    
    # Financial analysis fields
    acquirer_financial_profile: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    target_financial_profile: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    financial_synthesis: Optional[str] = Field(default=None, sa_column=Column(TEXT))
    acquirer_financial_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    target_financial_sources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="analysis"))

class CultureClash(SQLModel, table=True):
    __tablename__ = 'cultureclash'
    id: Optional[int] = Field(default=None, primary_key=True)
    topic: str = Field(index=True)
    description: str = Field(sa_column=Column(TEXT))
    severity: ClashSeverity = Field(sa_column=Column(TEXT, nullable=False))
    report_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("report.id")))
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="culture_clashes"))

class UntappedGrowth(SQLModel, table=True):
    __tablename__ = 'untappedgrowth'
    id: Optional[int] = Field(default=None, primary_key=True)
    description: str = Field(sa_column=Column(TEXT))
    potential_impact_score: int
    report_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), ForeignKey("report.id")))
    
    report: "Report" = SQLModelRelationship(sa_relationship=relationship("Report", back_populates="untapped_growths"))


# --- API Schemas ---
# FIX: Create dedicated "Read" schemas for nested models to break circular
# dependencies during serialization. The table models (e.g., ReportAnalysis)
# contain back-references to the parent Report model, which causes an
# infinite recursion loop when FastAPI tries to generate the response. These
# Read models omit the problematic back-reference.

class ReportAnalysisRead(SQLModel):
    id: Optional[int]
    cultural_compatibility_score: float
    affinity_overlap_score: float
    brand_archetype_summary: Optional[str]
    strategic_summary: Optional[str]
    report_id: uuid.UUID
    search_sources: Optional[List[Dict[str, Any]]]
    acquirer_sources: Optional[List[Dict[str, Any]]]
    target_sources: Optional[List[Dict[str, Any]]]
    acquirer_corporate_profile: Optional[str]
    target_corporate_profile: Optional[str]
    corporate_ethos_summary: Optional[str]
    acquirer_culture_sources: Optional[List[Dict[str, Any]]]
    target_culture_sources: Optional[List[Dict[str, Any]]]
    acquirer_financial_profile: Optional[str]
    target_financial_profile: Optional[str]
    financial_synthesis: Optional[str]
    acquirer_financial_sources: Optional[List[Dict[str, Any]]]
    target_financial_sources: Optional[List[Dict[str, Any]]]

class CultureClashRead(SQLModel):
    id: Optional[int]
    topic: str
    description: str
    severity: ClashSeverity
    report_id: uuid.UUID

class UntappedGrowthRead(SQLModel):
    id: Optional[int]
    description: str
    potential_impact_score: int
    report_id: uuid.UUID

class ReportCreate(SQLModel):
    title: str
    acquirer_brand: str
    target_brand: str

class ReportRead(SQLModel):
    id: uuid.UUID
    title: str
    acquirer_brand: Optional[str]
    target_brand: Optional[str]
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    user_id: int
    # Use the new Read schemas to prevent circular references
    analysis: Optional[ReportAnalysisRead] = None
    culture_clashes: List[CultureClashRead] = []
    untapped_growths: List[UntappedGrowthRead] = []

# DEFINITIVE FIX: Function to resolve all forward references before DB operations.
def rebuild_all_models():
    """
    This function forces the resolution of all forward-looking type hints
    in SQLModel and Pydantic models. It's crucial to call this at startup
    to prevent "type not defined" errors, especially in complex models
    with inter-dependencies.
    """
    logger.info("Rebuilding all model forward references...")
    # This is crucial. We must rebuild all models that have relationships
    # or forward references to ensure the type hints are resolved before FastAPI
    # attempts to perform serialization. This is especially true for the
    # DB models (User, Report, etc.) and the API models (ReportRead, etc.).
    User.model_rebuild()
    ReportAnalysis.model_rebuild()
    CultureClash.model_rebuild()
    UntappedGrowth.model_rebuild()
    Report.model_rebuild() # Depends on the above

    ReportCreate.model_rebuild()
    ReportAnalysisRead.model_rebuild()
    CultureClashRead.model_rebuild()
    UntappedGrowthRead.model_rebuild()
    ReportRead.model_rebuild() # Depends on the ...Read models
    logger.success("Model forward references rebuilt successfully.")

__all__ = [
    "User", "Report", "ReportAnalysis", "CultureClash", "UntappedGrowth",
    "ReportStatus", "ClashSeverity",
    "ReportCreate", "ReportRead",
    # Add new read models to __all__ for good practice
    "ReportAnalysisRead", "CultureClashRead", "UntappedGrowthRead",
    "rebuild_all_models"
]