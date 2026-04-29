"""server/api/v1/routes/interventions.py —— /api/v1/runs/:id/intervene（D-017 第 3.2 节）。

唯一 endpoint：POST /runs/{run_id}/intervene。

`Intervention` 模型直接复用 `models/runtime_models.Intervention`——含三种 kind
（inject_message / force_action / override_attribute）的字段约束。

返回 `EventRecord` —— intervention_applied 事件，前端可记录到事件流。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from models.runtime_models import EventRecord, Intervention

from server.api.deps import get_intervention_service
from server.services.intervention_service import InterventionService


router = APIRouter(prefix="/runs", tags=["interventions"])


@router.post(
    "/{run_id}/intervene",
    response_model=EventRecord,
    summary="应用人工干预",
)
def intervene(
    run_id: str,
    intervention: Intervention,
    svc: InterventionService = Depends(get_intervention_service),
) -> EventRecord:
    return svc.apply(run_id, intervention)
