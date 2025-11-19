from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.core.database import Base, SessionLocal, engine
from app.models.analysis import CompanyAnalysis
from app.models.company import AnalysisStatus, Company, CompanyStatus
from main import app


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> None:
    """Ensure database schema exists for export tests."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_auth_dependency() -> None:
    """Mock Cognito authentication for testing."""

    def _fake_user() -> dict:
        return {
            "user_id": "export-tester",
            "email": "exporter@example.com",
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
        cleanup = SessionLocal()
        cleanup.query(CompanyAnalysis).delete()
        cleanup.query(Company).delete()
        cleanup.commit()
        cleanup.close()
        db.close()


def _create_company(
    session,
    *,
    name: str = "NovaGeo Analytics",
    status: CompanyStatus = CompanyStatus.PENDING,
    analysis_status: AnalysisStatus = AnalysisStatus.COMPLETED,
) -> Company:
    company = Company(
        name=name,
        domain="novageo.io",
        website_url="https://novageo.io",
        email="info@novageo.io",
        phone="+15551234567",
        status=status,
        risk_score=68,
        analysis_status=analysis_status,
        current_step="complete",
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def _create_analysis(session, company_id) -> CompanyAnalysis:
    analysis = CompanyAnalysis(
        company_id=company_id,
        version=1,
        algorithm_version="1.0.0",
        submitted_data={
            "name": "NovaGeo Analytics",
            "domain": "novageo.io",
            "email": "info@novageo.io",
        },
        discovered_data={
            "domain_age": "6 months",
            "whois_privacy": True,
            "email_mx_match": False,
        },
        signals=[
            {"field": "domain_age", "value": "6 months", "status": "suspicious"},
            {"field": "email_mx_match", "value": False, "status": "mismatch"},
        ],
        risk_score=68,
        llm_summary="The company shows moderate risk due to a young domain age and email mismatches.",
        llm_details="WHOIS lookup indicates the domain was registered within the last year.",
        is_complete=True,
        failed_checks=["email_mx_match"],
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def test_export_json_returns_expected_payload(client: TestClient, session) -> None:
    company = _create_company(session)
    analysis = _create_analysis(session, company.id)

    response = client.get(f"/v1/companies/{company.id}/export/json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company"]["name"] == "NovaGeo Analytics"
    assert payload["analysis"]["version"] == analysis.version
    assert payload["analysis"]["risk_score"] == analysis.risk_score
    assert payload["analysis"]["signals"][0]["field"] == "domain_age"


def test_export_json_handles_missing_analysis(client: TestClient, session) -> None:
    company = _create_company(session, analysis_status=AnalysisStatus.PENDING)

    response = client.get(f"/v1/companies/{company.id}/export/json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"] is None


def test_export_json_missing_company_returns_404(client: TestClient) -> None:
    response = client.get(f"/v1/companies/{uuid4()}/export/json")
    assert response.status_code == 404


def test_export_pdf_streams_binary_document(client: TestClient, session) -> None:
    company = _create_company(session)
    _create_analysis(session, company.id)

    response = client.get(f"/v1/companies/{company.id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content[:4] == b"%PDF"


def test_export_pdf_without_analysis_still_generates_report(
    client: TestClient,
    session,
) -> None:
    company = _create_company(session, analysis_status=AnalysisStatus.PENDING)

    response = client.get(f"/v1/companies/{company.id}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_export_pdf_missing_company_returns_404(client: TestClient) -> None:
    response = client.get(f"/v1/companies/{uuid4()}/export/pdf")
    assert response.status_code == 404


