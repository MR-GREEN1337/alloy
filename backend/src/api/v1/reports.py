from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional
from sqlmodel import select, SQLModel
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from datetime import datetime
from fastapi.responses import StreamingResponse
import asyncio
import json

from src.db.postgresql import get_session
from src.db import models
from src.api.v1.auth import get_current_user
from src.services.react_agent import AlloyReActAgent
from src.services.docling import process_document_with_docling
from loguru import logger

router = APIRouter()

class ReportGeneratePayload(SQLModel):
    acquirer_brand: str
    target_brand: str
    title: str
    context: Optional[str] = None # This will now only be for user notes
    use_grounding: bool = False # This can be passed to the agent if needed

class DraftReportResponse(SQLModel):
    id: int
    status: models.ReportStatus
    created_at: datetime
    user_id: int

class ReportChatPayload(SQLModel):
    query: str
    context: str

class FileUploadResponse(SQLModel):
    filename: str
    content_type: str
    size_in_bytes: int
    message: str = "File processed successfully."

@router.post("/draft", response_model=DraftReportResponse, status_code=status.HTTP_201_CREATED)
async def create_draft_report(session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    logger.info(f"User {current_user.email} creating new draft report.")
    new_report = models.Report(user_id=current_user.id, status=models.ReportStatus.DRAFT)
    session.add(new_report)
    await session.commit()
    await session.refresh(new_report)
    logger.success(f"Draft report {new_report.id} created for user {current_user.email}.")
    return new_report

@router.post("/{report_id}/upload_context_file", response_model=FileUploadResponse)
async def upload_context_file(
    report_id: int, 
    file: UploadFile = File(...), 
    session: AsyncSession = Depends(get_session), 
    current_user: models.User = Depends(get_current_user)
):
    logger.info(f"User {current_user.email} uploading file '{file.filename}' for report {report_id}")
    report = await session.get(models.Report, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or access denied.")

    # Process file using the Docling service
    extracted_text = await process_document_with_docling(file)

    # Save extracted text to the report
    report.extracted_file_context = extracted_text
    session.add(report)
    await session.commit()

    logger.success(f"Saved extracted context from '{file.filename}' to report {report_id}")
    return FileUploadResponse(
        filename=file.filename,
        content_type=file.content_type,
        size_in_bytes=file.size
    )

@router.post("/{report_id}/generate")
async def generate_full_report_stream(
    report_id: int, payload: ReportGeneratePayload, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)
):
    
    async def event_generator():
        def yield_event(data: dict):
            # CORE FIX: This function now correctly handles the 'source' status
            # by passing the payload directly, and maps other statuses.
            status = data.get("status")
            if status == "source":
                return f"data: {json.dumps(data)}\n\n"

            event_map = {
                'thinking': 'info',
                'thought': 'info',
                'action': 'search', # Use 'search' as a generic action indicator
                'observation': 'info', # We won't show raw observations to the user
                'complete': 'complete',
                'error': 'error'
            }
            
            # Don't send raw observation events to the frontend
            if status == "observation":
                return ""
            
            event_data = { "status": event_map.get(status, 'info'), "message": data.get("message"), "payload": data.get("payload") }
            if status == 'action' and 'tool_name' in data.get('payload', {}):
                tool_name = data['payload']['tool_name']
                if 'qloo' in tool_name:
                    event_data['status'] = 'qloo'
                event_data['message'] = f"Using tool: {tool_name}"

            return f"data: {json.dumps(event_data)}\n\n"

        logger.info(f"User {current_user.email} starting ReAct Agent generation for draft ID: {report_id}")
        report = None
        
        try:
            # 1. SETUP REPORT
            report = await session.get(models.Report, report_id)
            if not report or report.user_id != current_user.id or report.status != models.ReportStatus.DRAFT:
                yield yield_event({"status": "error", "message": "Draft report not found or has been generated."})
                return

            report.acquirer_brand = payload.acquirer_brand
            report.target_brand = payload.target_brand
            report.title = payload.title
            report.status = models.ReportStatus.PENDING
            session.add(report)
            await session.commit()
            yield yield_event({"status": "info", "message": f"Starting analysis for {payload.acquirer_brand} vs. {payload.target_brand}"})

            # 2. RUN AGENT
            user_notes = payload.context or ""
            file_context = report.extracted_file_context or ""
            full_user_context = f"USER NOTES:\n{user_notes}\n\nDOCUMENT CONTEXT:\n{file_context}".strip()

            agent = AlloyReActAgent(
                acquirer_brand=report.acquirer_brand,
                target_brand=report.target_brand,
                user_context=full_user_context
            )
            
            # This will now yield 'source' events directly
            async for event in agent.run_stream():
                yield yield_event(event)
            
            # 3. SAVE FINAL REPORT
            final_report = agent.final_report
            if not final_report:
                raise Exception("Agent finished without providing a final report.")

            yield yield_event({"status": "saving", "message": "Saving final analysis to database"})
            
            analysis = models.ReportAnalysis(
                report_id=report.id,
                cultural_compatibility_score=final_report.get('cultural_compatibility_score', 0.0),
                affinity_overlap_score=final_report.get('affinity_overlap_score', 0.0),
                brand_archetype_summary=json.dumps(final_report.get('brand_archetype_summary', {})),
                strategic_summary=final_report.get('strategic_summary', 'Not generated.'),
                search_sources=[], 
                acquirer_sources=[],
                target_sources=[]
            )
            session.add(analysis)

            for clash in final_report.get('culture_clashes', []):
                session.add(models.CultureClash(report_id=report.id, **clash))
            for opportunity in final_report.get('untapped_growths', []):
                session.add(models.UntappedGrowth(report_id=report.id, **opportunity))
            
            report.status = models.ReportStatus.COMPLETED
            session.add(report)
            await session.commit()
            logger.success(f"ReAct Agent Report {report.id} completed successfully.")

            yield yield_event({"status": "complete", "message": "Report generated successfully!", "reportId": report_id})

        except Exception as e:
            logger.error(f"Stream generation failed for report {report_id}: {e}", exc_info=True)
            if report:
                report.status = models.ReportStatus.FAILED
                session.add(report)
                await session.commit()
            yield yield_event({"status": "error", "message": f"An unexpected error occurred: {e}"})
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{report_id}/chat", response_class=StreamingResponse)
async def chat_with_report(report_id: int, payload: ReportChatPayload, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    report = await session.get(models.Report, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    logger.info(f"User {current_user.email} is chatting with report {report_id}.")
    async def stream_response():
        try:
            async for chunk in generate_chat_response(payload.query, payload.context):
                yield chunk
        except Exception as e:
            logger.error(f"Error during chat stream for report {report_id}: {e}")
            yield "Sorry, I encountered an error while processing your request."
    return StreamingResponse(stream_response(), media_type="text/event-stream")

@router.get("/", response_model=List[models.ReportRead])
async def get_reports(session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    statement = (select(models.Report).where(models.Report.user_id == current_user.id, models.Report.status != models.ReportStatus.DRAFT).order_by(models.Report.created_at.desc()).options(selectinload(models.Report.analysis), selectinload(models.Report.culture_clashes), selectinload(models.Report.untapped_growths)))
    result = await session.execute(statement)
    reports = result.scalars().all()
    return reports

@router.get("/{report_id}", response_model=models.ReportRead)
async def get_report(report_id: int, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    statement = (select(models.Report).where(models.Report.id == report_id, models.Report.user_id == current_user.id).options(selectinload(models.Report.analysis), selectinload(models.Report.culture_clashes), selectinload(models.Report.untapped_growths)))
    result = await session.execute(statement)
    report = result.scalar_one_or_none()
    if not report or report.status == models.ReportStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: int, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    logger.info(f"User {current_user.email} attempting to delete report {report_id}")
    statement = select(models.Report).where(models.Report.id == report_id, models.Report.user_id == current_user.id)
    result = await session.execute(statement)
    report_to_delete = result.scalar_one_or_none()
    if not report_to_delete:
        logger.warning(f"Delete failed: Report {report_id} not found or user {current_user.email} does not have permission.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await session.delete(report_to_delete)
    await session.commit()
    logger.success(f"Successfully deleted report {report_id} for user {current_user.email}")
    return