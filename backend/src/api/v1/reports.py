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
    
    # We only need the LLM for summaries, not for lists that the agent already created.
    data_for_synthesis = {
        key: value for key, value in agent_data.items() 
        if key not in ['culture_clashes', 'untapped_growths']
    }

    prompt = f"""
    You are a senior M&A analyst from a top-tier investment bank. You have been provided with raw data from your junior research team.
    Your task is to synthesize this data into a final, professional due diligence report.

    **RAW DATA FOR SYNTHESIS:**
    ```json
    {json.dumps(data_for_synthesis, indent=2)}
    ```

    **YOUR TASK (Return a single JSON object):**
    Based *only* on the raw data provided, generate a complete report with the following keys:
    - "cultural_compatibility_score": A float (0-100). Base this on affinity_overlap_score. A high score is good. If Qloo fails, score is 0.0.
    - "affinity_overlap_score": A float, taken directly from the 'qloo_analysis'. If it's missing, this should be 0.0.
    - "brand_archetype_summary": An object with "acquirer_archetype" and "target_archetype" strings. Deduce these from their 'acquirer_profile' and 'target_profile'.
    - "corporate_ethos_summary": An object with "acquirer_ethos" and "target_ethos" strings. Synthesize a sharp, comparative analysis of each company's leadership, values, and work culture based on their 'acquirer_culture_profile' and 'target_culture_profile'.
    - "financial_synthesis": A string providing a comparative summary of the two companies' financial health and market positioning based on their respective financial profiles.
    - "strategic_summary": A string providing a concise, executive-level overview of all findings, combining brand, corporate, and financial insights into a final recommendation.

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
            "corporate_ethos_summary": {"acquirer_ethos": "N/A", "target_ethos": "N/A"},
            "financial_synthesis": "N/A"
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
async def generate_full_report_stream(report_id: int, payload: ReportGeneratePayload, current_user: models.User = Depends(get_current_user)):
    
    async def event_generator() -> AsyncGenerator[str, None]:
        def format_sse_event(data: dict) -> str:
            raw_status = data.get("status")
            if raw_status in ["action", "observation", "thinking"]: return ""
            event_data = {"payload": data.get("payload")}
            if raw_status == "source": event_data['status'] = 'source'
            elif raw_status == "thought": event_data['status'] = 'reasoning'; event_data['message'] = data.get("message", "").replace('**Thought**:', '').strip()
            elif raw_status == "complete": return "" 
            elif raw_status == "error": event_data['status'] = 'error'; event_data['message'] = data.get("message")
            else:
                action_payload = data.get('payload', {}); tool_name = action_payload.get('tool_name')
                if 'qloo' in tool_name: event_data['status'] = 'analysis'; event_data['message'] = "Performing comparative cultural analysis..."
                elif 'corporate_culture' in tool_name: event_data['status'] = 'analysis'; event_data['message'] = f"Investigating corporate culture at {action_payload.get('parameters', {}).get('brand_name')}"
                elif 'financial_and_market' in tool_name: event_data['status'] = 'analysis'; event_data['message'] = f"Analyzing market position of {action_payload.get('parameters', {}).get('brand_name')}"
                elif 'web_search' in tool_name: event_data['status'] = 'search'; event_data['message'] = f"Researching: {action_payload.get('parameters', {}).get('query')}"
                else: event_data['status'] = 'info'; event_data['message'] = data.get("message")
            return f"data: {json.dumps(event_data)}\n\n"

        report_to_generate = None
        generation_succeeded = False
        try:
            async with postgres_db.get_session() as session:
                report_to_generate = await session.get(models.Report, report_id)
                if not report_to_generate or report_to_generate.user_id != current_user.id or report_to_generate.status != models.ReportStatus.DRAFT:
                    error_data = json.dumps({'status': 'error', 'message': "Report not found or cannot be generated."})
                    yield f"data: {error_data}\n\n"
                    return

                report_to_generate.acquirer_brand = payload.acquirer_brand
                report_to_generate.target_brand = payload.target_brand
                report_to_generate.title = payload.title
                report_to_generate.status = models.ReportStatus.PENDING
                session.add(report_to_generate)
                await session.commit()
            
            yield f"data: {json.dumps({'status': 'info', 'message': f'Starting analysis for {payload.acquirer_brand} vs. {payload.target_brand}'})}\n\n"

            agent = AlloyReActAgent(report_to_generate.acquirer_brand, report_to_generate.target_brand, (report_to_generate.extracted_file_context or "") + "\n" + (payload.context or ""))
            async for event in agent.run_stream():
                sse_event = format_sse_event(event)
                if sse_event: yield sse_event
                if event.get("status") == "complete": break
            
            agent_final_data = agent.final_data if agent.final_data else {}
            
            yield f"data: {json.dumps({'status': 'synthesis', 'message': 'Synthesizing final report...'})}\n\n"
            final_report_summary = await synthesize_final_report(agent_final_data)

            yield f"data: {json.dumps({'status': 'saving', 'message': 'Saving final analysis to database'})}\n\n"
            async with postgres_db.get_session() as save_session:
                # Get the report object.
                save_report = await save_session.get(models.Report, report_id)
                if not save_report:
                    raise Exception("Report not found during save operation.")

                # The `cascade="all, delete-orphan"` on the relationship
                # means we don't need to manually delete the old analysis.
                # Simply creating and assigning a new one will replace it.
                
                # First, clear any existing related items that are managed by cascade
                # This ensures a clean slate before adding new ones.
                save_report.culture_clashes.clear()
                save_report.untapped_growths.clear()
                
                # Use a flush to persist the deletions before adding new items
                await save_session.flush()
                
                # Create the new analysis object
                new_analysis = models.ReportAnalysis(
                    report_id=save_report.id, # Redundant due to relationship but safe
                    cultural_compatibility_score=final_report_summary.get('cultural_compatibility_score', 0.0),
                    affinity_overlap_score=final_report_summary.get('affinity_overlap_score', 0.0),
                    brand_archetype_summary=json.dumps(final_report_summary.get('brand_archetype_summary', {})),
                    corporate_ethos_summary=json.dumps(final_report_summary.get('corporate_ethos_summary', {})),
                    strategic_summary=final_report_summary.get('strategic_summary', 'Analysis failed.'),
                    financial_synthesis=final_report_summary.get('financial_synthesis', 'Analysis failed.'),
                    acquirer_corporate_profile=agent_final_data.get('acquirer_culture_profile'),
                    target_corporate_profile=agent_final_data.get('target_culture_profile'),
                    acquirer_financial_profile=agent_final_data.get('acquirer_financial_profile'),
                    target_financial_profile=agent_final_data.get('target_financial_profile'),
                    search_sources=agent.all_sources.get('search_sources', []),
                    acquirer_sources=agent.all_sources.get('acquirer_sources', []),
                    target_sources=agent.all_sources.get('target_sources', []),
                    acquirer_culture_sources=agent.all_sources.get('acquirer_culture_sources', []),
                    target_culture_sources=agent.all_sources.get('target_culture_sources', []),
                    acquirer_financial_sources=agent.all_sources.get('acquirer_financial_sources', []),
                    target_financial_sources=agent.all_sources.get('target_financial_sources', [])
                )

                # Assign the new analysis to the report.
                save_report.analysis = new_analysis
                
                # Add new clashes and growths
                for clash in agent_final_data.get('culture_clashes', []):
                    save_report.culture_clashes.append(models.CultureClash(**clash))
                for growth in agent_final_data.get('untapped_growths', []):
                    save_report.untapped_growths.append(models.UntappedGrowth(**growth))
                
                # Update status and add to session
                save_report.status = models.ReportStatus.COMPLETED
                save_session.add(save_report)
                
                # The final commit will save everything due to the cascade settings.
                await save_session.commit()
                generation_succeeded = True
            
            yield f"data: {json.dumps({'status': 'complete', 'message': 'Report generated successfully!', 'payload': {'reportId': report_id}})}\n\n"
        except Exception as e:
            logger.error(f"Error in report generation stream for report {report_id}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred during report generation.'})}\n\n"
        finally:
            if not generation_succeeded and report_to_generate: await mark_report_as_failed(report_id)

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
        # Reconstruct the LLM summary payload for the PDF generator
        llm_summary = {
            "strategic_summary": report.analysis.strategic_summary,
            "financial_synthesis": report.analysis.financial_synthesis,
            "brand_archetypes": json.loads(report.analysis.brand_archetype_summary) if report.analysis.brand_archetype_summary else {},
            "corporate_ethos": json.loads(report.analysis.corporate_ethos_summary) if report.analysis.corporate_ethos_summary else {}
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