from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlmodel import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from src.db.postgresql import get_session
from src.db import models
from src.api.v1.auth import get_current_user
from src.services.report_generator import (
    get_qloo_taste_data,
    calculate_affinity_overlap,
    find_culture_clashes,
    find_untapped_growth,
    generate_llm_insights
)
from loguru import logger

router = APIRouter()

@router.post("/", response_model=models.ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_in: models.ReportCreate,
    session: AsyncSession = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    logger.info(f"User {current_user.email} creating report for {report_in.acquirer_brand} vs {report_in.target_brand}")
    
    report = models.Report.model_validate(report_in, update={"user_id": current_user.id, "status": models.ReportStatus.PENDING})
    session.add(report)
    await session.commit()
    await session.refresh(report)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            acquirer_data = await get_qloo_taste_data(report.acquirer_brand, client)
            target_data = await get_qloo_taste_data(report.target_brand, client)
        
        if not acquirer_data or not target_data:
            raise HTTPException(status_code=404, detail="Could not retrieve taste data for one or both brands.")

        affinity_score = calculate_affinity_overlap(acquirer_data, target_data)
        clashes = find_culture_clashes(acquirer_data, target_data)
        opportunities = find_untapped_growth(acquirer_data, target_data)

        acquirer_taste_str = ", ".join([item['name'] for item in acquirer_data[:20]])
        target_taste_str = ", ".join([item['name'] for item in target_data[:20]])
        llm_insights = await generate_llm_insights(report.acquirer_brand, report.target_brand, acquirer_taste_str, target_taste_str)

        analysis = models.ReportAnalysis(
            report_id=report.id,
            cultural_compatibility_score=affinity_score,
            affinity_overlap_score=affinity_score,
            brand_archetype_summary=llm_insights['brand_archetype_summary'],
            strategic_summary=llm_insights['strategic_summary']
        )
        session.add(analysis)

        for clash in clashes:
            session.add(models.CultureClash(report_id=report.id, **clash))
        
        for opportunity in opportunities:
            session.add(models.UntappedGrowth(report_id=report.id, **opportunity))

        report.status = models.ReportStatus.COMPLETED
        logger.success(f"Report {report.id} completed successfully.")

    except Exception as e:
        report.status = models.ReportStatus.FAILED
        logger.error(f"Report generation failed for report {report.id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        session.add(report)
        await session.commit()
        await session.refresh(report)

    statement = select(models.Report).where(models.Report.id == report.id).options(
        selectinload(models.Report.analysis),
        selectinload(models.Report.culture_clashes),
        selectinload(models.Report.untapped_growths)
    )
    final_report = (await session.execute(statement)).scalar_one_or_none()
    return final_report


@router.get("/", response_model=List[models.ReportRead])
async def get_reports(
    session: AsyncSession = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    statement = (
        select(models.Report)
        .where(models.Report.user_id == current_user.id)
        .order_by(models.Report.created_at.desc())
        .options(
            selectinload(models.Report.analysis),
            selectinload(models.Report.culture_clashes),
            selectinload(models.Report.untapped_growths)
        )
    )
    result = await session.execute(statement)
    reports = result.scalars().all()
    return reports

@router.get("/{report_id}", response_model=models.ReportRead)
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    statement = (
        select(models.Report)
        .where(models.Report.id == report_id, models.Report.user_id == current_user.id)
        .options(
            selectinload(models.Report.analysis),
            selectinload(models.Report.culture_clashes),
            selectinload(models.Report.untapped_growths)
        )
    )
    result = await session.execute(statement)
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
    return report

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deletes a report owned by the current user.
    """
    logger.info(f"User {current_user.email} attempting to delete report {report_id}")
    
    # First, get the report and ensure the current user owns it
    statement = select(models.Report).where(
        models.Report.id == report_id,
        models.Report.user_id == current_user.id
    )
    result = await session.execute(statement)
    report_to_delete = result.scalar_one_or_none()

    if not report_to_delete:
        logger.warning(f"Delete failed: Report {report_id} not found or user {current_user.email} does not have permission.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # If found, delete it
    await session.delete(report_to_delete)
    await session.commit()
    
    logger.success(f"Successfully deleted report {report_id} for user {current_user.email}")
    return