from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from agentos.config import ComplianceConfig
from agentos.domain.compliance import (RANGE_OPERATORS, CheckOperator,
                                       ComplianceQuestion, ComplianceReport,
                                       ExecutableCheck, Requirement)
from agentos.domain.sources import Sensitivity, Source, SourceKind
from agentos.engine import build_engine
from agentos.identity.principal import Principal
from agentos.persistence.kv import SqliteStore

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class ExecutableCheckModel(BaseModel):
    metric: str
    unit: str
    operator: str
    threshold: float
    upper: float | None = None


class RequirementModel(BaseModel):
    id: str
    text: str
    check: ExecutableCheckModel | None = None


class SourceModel(BaseModel):
    id: str
    kind: str
    uri: str


class PrincipalModel(BaseModel):
    id: str
    roles: list[str]
    tenant_id: str | None = None


class PolicyModel(BaseModel):
    role_clearances: dict[str, str] | None = None
    groundedness_threshold: float | None = None
    support_threshold: float | None = None
    token_budget: int | None = None


class ComplianceRequest(BaseModel):
    question_id: str
    text: str = ""
    requirements: list[RequirementModel]
    sources: list[SourceModel]
    principal: PrincipalModel
    policy: PolicyModel | None = None


class FindingModel(BaseModel):
    requirement_id: str
    claim_id: str
    verdict: str
    groundedness_score: float
    supporting_span_ids: list[str]
    escalated_to_human: bool


class ComplianceResponse(BaseModel):
    question_id: str
    findings: list[FindingModel]


def require_api_key(provided: str | None = Depends(_API_KEY_HEADER)) -> None:
    expected = os.environ.get("AGENTOS_API_KEY", "dev-key")
    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid api key")


def _request_backend():
    path = os.environ.get("AGENTOS_DB_PATH")
    return SqliteStore(path) if path else None


def _to_config(model: PolicyModel | None) -> ComplianceConfig:
    if model is None:
        return ComplianceConfig()
    overrides = {}
    if model.role_clearances is not None:
        try:
            overrides["role_clearances"] = {
                role: Sensitivity(value) for role, value in model.role_clearances.items()}
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown sensitivity in role clearances")
    if model.groundedness_threshold is not None:
        overrides["groundedness_threshold"] = model.groundedness_threshold
    if model.support_threshold is not None:
        overrides["support_threshold"] = model.support_threshold
    if model.token_budget is not None:
        overrides["token_budget"] = model.token_budget
    return ComplianceConfig(**overrides)


def _to_requirement(model: RequirementModel) -> Requirement:
    check = None
    if model.check is not None:
        try:
            operator = CheckOperator(model.check.operator)
        except ValueError:
            raise HTTPException(status_code=400, detail="unknown check operator")
        if operator in RANGE_OPERATORS and model.check.upper is None:
            raise HTTPException(status_code=400, detail="range check requires an upper bound")
        check = ExecutableCheck(model.check.metric, model.check.unit, operator,
                                model.check.threshold, model.check.upper)
    return Requirement(model.id, model.text, check)


def _to_question(request: ComplianceRequest) -> ComplianceQuestion:
    try:
        sources = [Source(item.id, SourceKind(item.kind), item.uri) for item in request.sources]
    except ValueError:
        raise HTTPException(status_code=400, detail="unknown source kind")
    requirements = [_to_requirement(item) for item in request.requirements]
    return ComplianceQuestion(request.question_id, request.text, requirements, sources)


def _to_principal(model: PrincipalModel, config: ComplianceConfig) -> Principal:
    known_roles = set(config.role_clearances)
    unknown = [role for role in model.roles if role not in known_roles]
    if unknown:
        raise HTTPException(status_code=400, detail=f"unknown role: {unknown[0]}")
    return Principal(model.id, set(model.roles), model.tenant_id)


def _to_response(report: ComplianceReport) -> ComplianceResponse:
    return ComplianceResponse(
        question_id=report.question_id,
        findings=[FindingModel(
            requirement_id=finding.requirement_id,
            claim_id=finding.claim_id,
            verdict=finding.verdict.value,
            groundedness_score=finding.groundedness_score,
            supporting_span_ids=finding.supporting_span_ids,
            escalated_to_human=finding.escalated_to_human,
        ) for finding in report.findings])


app = FastAPI(title="AgentOS Compliance API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/compliance/check", response_model=ComplianceResponse)
def check_compliance(request: ComplianceRequest,
                     _: None = Depends(require_api_key)) -> ComplianceResponse:
    config = _to_config(request.policy)
    report = build_engine(backend=_request_backend(), config=config).run(
        _to_question(request), _to_principal(request.principal, config))
    return _to_response(report)
