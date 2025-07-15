from __future__ import annotations
import enum
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, DateTime, Enum as SAEnum, func

class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Report(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    acquirer_brand: str
    target_brand: str
    
    status: ReportStatus = Field(
        sa_column=Column(SAEnum(ReportStatus)), 
        default=ReportStatus.PENDING,
        nullable=False
    )
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        nullable=False
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        nullable=False
    )

    # Foreign Key to User
    user_id: int = Field(foreign_key="user.id")

    # Relationship back to User
    user: "User" = Relationship(back_populates="reports")

    # One-to-one relationship to the analysis summary
    analysis: Optional["ReportAnalysis"] = Relationship(
        back_populates="report", 
        sa_relationship_kwargs={'uselist': False}
    )

    # One-to-many relationships
    culture_clashes: List["CultureClash"] = Relationship(back_populates="report")
    untapped_growths: List["UntappedGrowth"] = Relationship(back_populates="report")