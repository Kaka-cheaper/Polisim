"""server/api/v1/routes/analysis.py —— /api/v1/runs/:id/analysis（D-017 第 3.4 节）。

两个 endpoints：
- GET /runs/{run_id}/analysis?enhance=...   读取或生成
- POST /runs/{run_id}/analyze               显式重跑（前端"重跑增强"按钮）

GET 与 POST 的语义差别（D-017 第 3.4 节）：
- GET：表示"读取"——服务端可视为 idempotent
- POST：表示"重新生成"——`AnalyzeRequest.llm_enhance` 决定是否含 Phase C
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from models.analysis_models import AnalysisResult

from server.api.deps import get_analysis_service
from server.api.v1.schemas import AnalyzeRequest
from server.services.analysis_service import AnalysisService


router = APIRouter(prefix="/runs", tags=["analysis"])


@router.get(
    "/{run_id}/analysis",
    response_model=AnalysisResult,
    summary="获取分析报告（含可选 LLM 增强）",
)
def get_analysis(
    run_id: str,
    enhance: bool = Query(False, description="是否触发 Phase C LLM 增强"),
    svc: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResult:
    return svc.analyze(run_id, llm_enhance=enhance)


@router.post(
    "/{run_id}/analyze",
    response_model=AnalysisResult,
    summary="显式重新生成分析报告",
)
def post_analyze(
    run_id: str,
    req: AnalyzeRequest,
    svc: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResult:
    return svc.analyze(run_id, llm_enhance=req.llm_enhance)
