import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
import json

from src.db import models
from src.db.postgresql import postgres_db

@pytest.mark.asyncio
async def test_create_and_get_reports(authorized_client: AsyncClient, test_user: models.User, db_session: AsyncSession):
    # Create a draft report
    response = await authorized_client.post("/api/v1/reports/draft")
    assert response.status_code == status.HTTP_201_CREATED
    draft_report = response.json()
    assert draft_report["status"] == "DRAFT"
    assert draft_report["user_id"] == test_user.id

    # Create a completed report manually for testing GET
    completed_report = models.Report(
        user_id=test_user.id,
        title="Completed Test Report",
        acquirer_brand="Acquirer",
        target_brand="Target",
        status=models.ReportStatus.COMPLETED
    )
    db_session.add(completed_report)
    await db_session.commit()
    await db_session.refresh(completed_report)

    # Get all non-draft reports for the user
    response = await authorized_client.get("/api/v1/reports/")
    assert response.status_code == status.HTTP_200_OK
    reports_list = response.json()
    assert len(reports_list) == 1
    assert reports_list[0]["id"] == completed_report.id
    assert reports_list[0]["title"] == "Completed Test Report"

    # Get a specific report by ID
    response = await authorized_client.get(f"/api/v1/reports/{completed_report.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Completed Test Report"

@pytest.mark.asyncio
async def test_delete_report(authorized_client: AsyncClient, test_user: models.User, db_session: AsyncSession):
    report_to_delete = models.Report(user_id=test_user.id, status=models.ReportStatus.COMPLETED)
    db_session.add(report_to_delete)
    await db_session.commit()
    await db_session.refresh(report_to_delete)
    report_id = report_to_delete.id

    # Delete the report
    response = await authorized_client.delete(f"/api/v1/reports/{report_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's gone from the database using a new session to avoid cache issues
    async with postgres_db.get_session() as session:
        deleted_report = await session.get(models.Report, report_id)
        assert deleted_report is None

@pytest.mark.asyncio
async def test_generate_report_stream_mocked(authorized_client: AsyncClient, test_user: models.User, db_session: AsyncSession, mocker):
    # --- Mocks Setup ---
    mock_agent_instance = mocker.MagicMock()
    async def mock_run_stream():
        yield {"status": "info", "message": "Agent started"}
        yield {"status": "complete"}

    mock_agent_instance.run_stream.return_value = mock_run_stream()
    mock_agent_instance.final_data = {
        "qloo_analysis": {"affinity_overlap_score": 55.5}, "culture_clashes": [], "untapped_growths": [],
        "acquirer_culture_profile": "Mock culture", "target_culture_profile": "Mock culture",
        "acquirer_financial_profile": "Mock finance", "target_financial_profile": "Mock finance"
    }
    mock_agent_instance.all_sources = {}
    mocker.patch('src.api.v1.reports.AlloyReActAgent', return_value=mock_agent_instance)

    mocker.patch('src.api.v1.reports.synthesize_final_report', return_value={
        "cultural_compatibility_score": 88.0, "affinity_overlap_score": 55.5,
        "strategic_summary": "Mocked summary.", "brand_archetype_summary": {},
        "corporate_ethos_summary": {}, "financial_synthesis": "Mocked financial synthesis."
    })
    
    # --- Test Execution ---
    draft_report = models.Report(user_id=test_user.id, status=models.ReportStatus.DRAFT)
    db_session.add(draft_report)
    await db_session.commit()
    await db_session.refresh(draft_report)
    report_id_to_check = draft_report.id
    
    payload = {"acquirer_brand": "Test Acquirer", "target_brand": "Test Target", "title": "Mock Report"}
    
    events = []
    async with authorized_client.stream("POST", f"/api/v1/reports/{report_id_to_check}/generate", json=payload, timeout=10) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[6:]))

    # --- Assertions ---
    final_event = events[-1] if events else {}
    assert final_event.get("status") == "complete", f"Stream did not complete successfully. Last event: {final_event}"
    assert final_event.get("payload", {}).get("reportId") == report_id_to_check

    # Assert the database state was updated correctly using a fresh session
    async with postgres_db.get_session() as session:
        final_report = await session.get(models.Report, report_id_to_check)
        assert final_report is not None
        assert final_report.status == models.ReportStatus.COMPLETED
        # To check analysis, we need to load the relationship
        await session.refresh(final_report, attribute_names=["analysis"])
        assert final_report.analysis is not None
        assert final_report.analysis.cultural_compatibility_score == 88.0