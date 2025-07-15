from __future__ import annotations
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, DateTime, func

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = Field(default=None)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        nullable=False
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        nullable=False
    )

    reports: List["Report"] = Relationship(back_populates="user")