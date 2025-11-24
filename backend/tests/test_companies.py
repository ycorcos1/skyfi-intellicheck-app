from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.database import Base, SessionLocal, engine
from app.models.analysis import CompanyAnalysis
from app.models.company import AnalysisStatus, Company, CompanyStatus
from app.services import sqs_service
from main import app


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> None:
    """Create database schema for tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_auth_dependency() -> None:
    """Bypass Cognito authentication for API tests."""

    def _fake_user() -> Dict[str, Any]:
        return {
            "user_id": "test-user",
            "email": "test@example.com",
            "claims": {},
        }

    app.dependency_overrides[get_current_user] = _fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        cleanup = SessionLocal()
        cleanup.query(CompanyAnalysis).delete()
        cleanup.query(Company).delete()
        cleanup.commit()
        cleanup.close()


@pytest.fixture
def fake_sqs(monkeypatch: pytest.MonkeyPatch):
    """Provide a fake SQS service that records enqueued messages."""

    class _FakeSQSService:
        def __init__(self) -> None:
            self.calls: List[Dict[str, Any]] = []

        def enqueue_analysis(
            self,
            company_id: str,
            retry_mode: str = "full",
            failed_checks: List[str] | None = None,
            correlation_id: str | None = None,
        ) -> Dict[str, str]:
            call = {
                "company_id": company_id,
                "retry_mode": retry_mode,
                "failed_checks": failed_checks or [],
                "correlation_id": correlation_id,
            }
            self.calls.append(call)
            return {"MessageId": f"msg-{len(self.calls)}"}

    fake_service = _FakeSQSService()
    monkeypatch.setattr(
        "app.api.v1.endpoints.companies.get_sqs_service",
        lambda: fake_service,
    )
    monkeypatch.setattr(
        sqs_service,
        "_sqs_service",
        fake_service,
        raising=False,
    )
    return fake_service


def _create_company(
    session,
    *,
    name: str = "Test Company",
    status: CompanyStatus = CompanyStatus.PENDING,
    analysis_status: AnalysisStatus = AnalysisStatus.COMPLETE,
    current_step: str | None = "complete",
) -> Company:
    company = Company(
        name=name,
        domain="example.com",
        website_url="https://example.com",
        email="info@example.com",
        phone="+15555550123",
        status=status,
        analysis_status=analysis_status,
        current_step=current_step,
        risk_score=42,
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _create_analysis(
    session,
    company_id: UUID,
    *,
    version: int = 1,
    failed_checks: List[str] | None = None,
    is_complete: bool = True,
) -> CompanyAnalysis:
    analysis = CompanyAnalysis(
        company_id=company_id,
        version=version,
        algorithm_version="1.0.0",
        submitted_data={"name": "Test Company"},
        discovered_data={"whois": {"domain_age_days": 400}},
        signals=[],
        risk_score=50,
        llm_summary=None,
        llm_details=None,
        is_complete=is_complete,
        failed_checks=failed_checks or [],
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def test_reanalyze_full_enqueues_message(
    client: TestClient,
    session,
    fake_sqs,
) -> None:
    company = _create_company(session, analysis_status=AnalysisStatus.COMPLETE)

    response = client.post(
        f"/v1/companies/{company.id}/reanalyze",
        json={"retry_failed_only": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retry_mode"] == "full"
    assert payload["message"] == "Analysis queued"
    assert "queued_at" in payload

    assert len(fake_sqs.calls) == 1
    assert fake_sqs.calls[0]["company_id"] == str(company.id)
    assert fake_sqs.calls[0]["retry_mode"] == "full"

    refreshed = session.get(Company, company.id)
    assert refreshed.analysis_status == AnalysisStatus.PENDING
    assert refreshed.current_step is None


def test_reanalyze_failed_only_uses_failed_checks(
    client: TestClient,
    session,
    fake_sqs,
) -> None:
    company = _create_company(session, analysis_status=AnalysisStatus.COMPLETE)
    _create_analysis(session, company.id, failed_checks=["whois", "mx_validation"], is_complete=False)

    response = client.post(
        f"/v1/companies/{company.id}/reanalyze",
        json={"retry_failed_only": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retry_mode"] == "failed_only"

    assert len(fake_sqs.calls) == 1
    assert fake_sqs.calls[0]["failed_checks"] == ["whois", "mx_validation"]


def test_reanalyze_failed_only_without_failed_checks_returns_400(
    client: TestClient,
    session,
    fake_sqs,
) -> None:
    company = _create_company(session, analysis_status=AnalysisStatus.COMPLETE)
    _create_analysis(session, company.id, failed_checks=[], is_complete=True)

    response = client.post(
        f"/v1/companies/{company.id}/reanalyze",
        json={"retry_failed_only": True},
    )

    assert response.status_code == 400
    assert "no failed checks" in response.json()["detail"].lower()
    assert not fake_sqs.calls


def test_update_company_status_valid_transition(
    client: TestClient,
    session,
) -> None:
    company = _create_company(session, status=CompanyStatus.PENDING)

    response = client.patch(
        f"/v1/companies/{company.id}/status",
        json={"action": "approve"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == CompanyStatus.APPROVED

    refreshed = session.get(Company, company.id)
    assert refreshed.status == CompanyStatus.APPROVED


def test_update_company_status_invalid_transition(
    client: TestClient,
    session,
) -> None:
    company = _create_company(session, status=CompanyStatus.FRAUDULENT)

    response = client.patch(
        f"/v1/companies/{company.id}/status",
        json={"action": "approve"},
    )

    assert response.status_code == 400


def test_analysis_status_endpoint_in_progress(
    client: TestClient,
    session,
) -> None:
    company = _create_company(
        session,
        analysis_status=AnalysisStatus.IN_PROGRESS,
        current_step="mx_validation",
    )

    response = client.get(f"/v1/companies/{company.id}/analysis/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_status"] == AnalysisStatus.IN_PROGRESS
    assert payload["progress_percentage"] == 40
    assert payload["current_step"] == "mx_validation"


def test_analysis_status_endpoint_failed_returns_failed_checks(
    client: TestClient,
    session,
) -> None:
    company = _create_company(
        session,
        analysis_status=AnalysisStatus.COMPLETE,
        current_step=None,
    )
    _create_analysis(session, company.id, failed_checks=["llm_processing"], is_complete=False)

    response = client.get(f"/v1/companies/{company.id}/analysis/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_status"] == AnalysisStatus.COMPLETE
    assert payload["progress_percentage"] == 100
    assert payload["failed_checks"] == ["llm_processing"]

