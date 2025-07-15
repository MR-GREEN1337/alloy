from __future__ import annotations
import enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Enum as SAEnum, TEXT

class ClashSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ReportAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    cultural_compatibility_score: float = Field(index=True)
    affinity_overlap_score: float
    
    brand_archetype_summary: str = Field(sa_column=Column(TEXT))
    strategic_summary: str = Field(sa_column=Column(TEXT))

    # Foreign Key to Report
    report_id: int = Field(foreign_key="report.id")

    # Relationship back to Report
    report: "Report" = Relationship(back_populates="analysis")

class CultureClash(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    topic: str = Field(index=True)
    description: str = Field(sa_column=Column(TEXT))
    severity: ClashSeverity = Field(sa_column=Column(SAEnum(ClashSeverity)))

    # Foreign Key to Report
    report_id: int = Field(foreign_key="report.id")

    # Relationship back to Report
    report: "Report" = Relationship(back_populates="culture_clashes")

class UntappedGrowth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    description: str = Field(sa_column=Column(TEXT))
    potential_impact_score: int # Score from 1-10

    # Foreign Key to Report
    report_id: int = Field(foreign_key="report.id")

    # Relationship back to Report
    report: "Report" = Relationship(back_populates="untapped_growths")