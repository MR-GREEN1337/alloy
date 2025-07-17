from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List, Optional, AsyncGenerator
from sqlmodel import select, SQLModel
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from fastapi.responses import StreamingResponse, Response
import json
import asyncio
import google.generativeai as genai

from src.db.postgresql import get_session, postgres_db
from src.db import models
from src.core.settings import get_settings
from src.api.v1.auth import get_current_user
from src.services.react_agent import AlloyReActAgent
from src.services.docling import process_document_with_docling
from src.services.report_generator import generate_chat_response
from src.services.pdf_generator import create_report_pdf
from loguru import logger

router = APIRouter()
settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

# --- Pydantic Models for API ---
class ReportGeneratePayload(SQLModel):
    acquirer_brand: str
    target_brand: str
    title: str
    context: Optional[str] = None
    use_grounding: bool = False

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

# --- Helper Functions ---
async def mark_report_as_failed(report_id: int) -> None:
    try:
        async with postgres_db.get_session() as session:
            report = await session.get(models.Report, report_id)
            if report and report.status == models.ReportStatus.PENDING:
                report.status = models.ReportStatus.FAILED
                session.add(report)
                await session.commit()
                logger.info(f"Successfully marked report {report_id} as FAILED.")
    except Exception as e:
        logger.error(f"Could not mark report {report_id} as FAILED: {e}")

async def synthesize_final_report(agent_data: dict) -> dict:
    """Takes the agent's gathered data and synthesizes the final report with an LLM call."""
    logger.info("Synthesizing final report from agent data.")
    model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)
    
    prompt = f"""
    You are a senior M&A analyst. You have been provided with raw data from your junior research team.
    Your task is to synthesize this data into a final, professional due diligence report.

    **RAW DATA:**
    ```json
    {json.dumps(agent_data, indent=2)}
    ```

    **YOUR TASK:**
    Based *only* on the raw data provided, generate a complete report as a single JSON object with the following keys:
    - "cultural_compatibility_score": A float between 0 and 100. Base this on the affinity_overlap_score and the severity of clashes. A high overlap and low severity clashes should result in a high score. If Qloo analysis failed, this should be 0.0.
    - "affinity_overlap_score": A float, taken directly from the 'qloo_analysis'. If it's missing, this should be 0.0.
    - "brand_archetype_summary": An object with "acquirer_archetype" and "target_archetype" strings. Deduce these from their respective profiles.
    - "strategic_summary": A string providing a concise, executive-level overview of the findings, including risks and opportunities.
    - "culture_clashes": A list of objects, each with "topic" (string), "description" (string), and "severity" ('LOW', 'MEDIUM', or 'HIGH'). Derive these from the 'unique_tastes' in the Qloo analysis.
    - "untapped_growths": A list of objects, each with "description" (string) and "potential_impact_score" (integer 1-10). Derive these from the 'shared_affinities' in the Qloo analysis.

    Return ONLY the final JSON object.
    """
    
    try:
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        report = json.loads(response.text)
        report['cultural_compatibility_score'] = report.get('cultural_compatibility_score', 0.0)
        report['affinity_overlap_score'] = report.get('affinity_overlap_score', 0.0)
        return report
    except Exception as e:
        logger.error(f"Final report synthesis failed: {e}")
        return {
            "strategic_summary": "Analysis failed during final synthesis. Key data may be missing.",
            "cultural_compatibility_score": 0.0,
            "affinity_overlap_score": agent_data.get('qloo_analysis', {}).get('affinity_overlap_score', 0.0),
            "brand_archetype_summary": {"acquirer_archetype": "N/A", "target_archetype": "N/A"},
            "culture_clashes": [], "untapped_growths": []
        }

# --- API Endpoints ---
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
async def upload_context_file(report_id: int, file: UploadFile = File(...), session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    report = await session.get(models.Report, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or access denied.")
    extracted_text = await process_document_with_docling(file)
    report.extracted_file_context = extracted_text
    session.add(report)
    await session.commit()
    return FileUploadResponse(filename=file.filename, content_type=file.content_type or "application/octet-stream", size_in_bytes=file.size)

@router.post("/{report_id}/generate")
async def generate_full_report_stream(report_id: int, payload: ReportGeneratePayload, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    
    async def event_generator() -> AsyncGenerator[str, None]:
        def format_sse_event(data: dict) -> str:
            raw_status = data.get("status")
            if raw_status in ["action", "observation", "thinking"]: return ""
            event_data = {"payload": data.get("payload")}
            if raw_status == "source": event_data['status'] = 'source'
            elif raw_status == "thought": event_data['status'] = 'reasoning'; event_data['message'] = data.get("message")
            elif raw_status == "complete": return "" 
            elif raw_status == "error": event_data['status'] = 'error'; event_data['message'] = data.get("message")
            else:
                action_payload = data.get('payload', {}); tool_name = action_payload.get('tool_name')
                if 'qloo' in tool_name: event_data['status'] = 'analysis'; event_data['message'] = "Performing comparative cultural analysis..."
                elif 'web_search' in tool_name: event_data['status'] = 'search'; event_data['message'] = f"Researching: {action_payload.get('parameters', {}).get('query')}"
                else: event_data['status'] = 'info'; event_data['message'] = data.get("message")
            return f"data: {json.dumps(event_data)}\n\n"

        report = None
        generation_succeeded = False
        try:
            report = await session.get(models.Report, report_id)
            if not report or report.user_id != current_user.id or report.status != models.ReportStatus.DRAFT:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found or cannot be generated.")
            
            report.acquirer_brand, report.target_brand, report.title, report.status = payload.acquirer_brand, payload.target_brand, payload.title, models.ReportStatus.PENDING
            session.add(report); await session.commit()
            yield f"data: {json.dumps({'status': 'info', 'message': f'Starting analysis for {payload.acquirer_brand} vs. {payload.target_brand}'})}\n\n"

            agent = AlloyReActAgent(report.acquirer_brand, report.target_brand, (report.extracted_file_context or "") + "\n" + (payload.context or ""))
            async for event in agent.run_stream():
                sse_event = format_sse_event(event)
                if sse_event: yield sse_event
                if event.get("status") == "complete": break
            
            if not agent.final_data: agent.final_data = {}

            yield f"data: {json.dumps({'status': 'synthesis', 'message': 'Synthesizing final report...'})}\n\n"
            final_report = await synthesize_final_report(agent.final_data)

            yield f"data: {json.dumps({'status': 'saving', 'message': 'Saving final analysis to database'})}\n\n"
            async with postgres_db.get_session() as save_session:
                stmt = select(models.Report).options(selectinload(models.Report.analysis)).where(models.Report.id == report_id)
                result = await save_session.execute(stmt)
                save_report = result.scalar_one_or_none()
                if not save_report: raise Exception("Report not found during save.")
                if save_report.analysis: await save_session.delete(save_report.analysis); await save_session.flush()
                
                analysis = models.ReportAnalysis(
                    report_id=save_report.id,
                    cultural_compatibility_score=final_report.get('cultural_compatibility_score', 0.0),
                    affinity_overlap_score=final_report.get('affinity_overlap_score', 0.0),
                    brand_archetype_summary=json.dumps(final_report.get('brand_archetype_summary', {})),
                    strategic_summary=final_report.get('strategic_summary', 'Analysis failed.'),
                    search_sources=agent.all_sources.get('search_sources', []),
                    acquirer_sources=agent.all_sources.get('acquirer_sources', []),
                    target_sources=agent.all_sources.get('target_sources', [])
                )
                save_session.add(analysis)

                for clash in final_report.get('culture_clashes', []): save_session.add(models.CultureClash(report_id=save_report.id, **clash))
                for growth in final_report.get('untapped_growths', []): save_session.add(models.UntappedGrowth(report_id=save_report.id, **growth))
                
                save_report.status = models.ReportStatus.COMPLETED
                save_session.add(save_report)
                await save_session.commit()
                generation_succeeded = True
            
            yield f"data: {json.dumps({'status': 'complete', 'message': 'Report generated successfully!', 'payload': {'reportId': report_id}})}\n\n"
        except Exception as e:
            logger.error(f"Error in report generation stream for report {report_id}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred during report generation.'})}\n\n"
        finally:
            if not generation_succeeded and report: await mark_report_as_failed(report_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/{report_id}/download-pdf")
async def download_report_pdf(report_id: int, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    """Generates and downloads a professional PDF report."""
    logger.info(f"User {current_user.email} requested PDF for report {report_id}")
    
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
    
    if not report or report.status != models.ReportStatus.COMPLETED or not report.analysis:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found or not complete.")

    try:
        # CORE FIX: The PDF needs the qualitative summary from the LLM.
        # We can't regenerate it, but we can extract it from the saved analysis.
        # This simulates the hybrid approach without needing a live agent run.
        llm_summary = {
            "strategic_summary": report.analysis.strategic_summary,
            "brand_archetypes": json.loads(report.analysis.brand_archetype_summary)
        }
        
        pdf_bytes = create_report_pdf(report, llm_summary)
        
        filename = f"Alloy_Report_{report.acquirer_brand}_vs_{report.target_brand}.pdf"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for report {report_id}: {e}", exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to generate PDF report.")

@router.get("/", response_model=List[models.ReportRead])
async def get_reports(session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    statement = select(models.Report).where(models.Report.user_id == current_user.id, models.Report.status != models.ReportStatus.DRAFT).order_by(models.Report.created_at.desc()).options(selectinload(models.Report.analysis), selectinload(models.Report.culture_clashes), selectinload(models.Report.untapped_growths))
    result = await session.execute(statement)
    return list(result.scalars().all())

@router.get("/{report_id}", response_model=models.ReportRead)
async def get_report(report_id: int, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    statement = select(models.Report).where(models.Report.id == report_id, models.Report.user_id == current_user.id).options(selectinload(models.Report.analysis), selectinload(models.Report.culture_clashes), selectinload(models.Report.untapped_growths))
    result = await session.execute(statement)
    report = result.scalar_one_or_none()
    if not report or (report.status == models.ReportStatus.DRAFT and report.user_id != current_user.id): raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: int, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    report_to_delete = await session.get(models.Report, report_id)
    if not report_to_delete or report_to_delete.user_id != current_user.id: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")
    await session.delete(report_to_delete); await session.commit()

@router.post("/{report_id}/chat", response_class=StreamingResponse)
async def chat_with_report(report_id: int, payload: ReportChatPayload, session: AsyncSession = Depends(get_session), current_user: models.User = Depends(get_current_user)):
    report = await session.get(models.Report, report_id)
    if not report or report.user_id != current_user.id: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found.")
    async def stream_response():
        try:
            async for chunk in generate_chat_response(payload.query, payload.context): yield chunk
        except Exception as e:
            logger.error(f"Error during chat stream for report {report_id}: {e}")
            yield "Sorry, I encountered an error while processing your request."
    return StreamingResponse(stream_response(), media_type="text/event-stream")