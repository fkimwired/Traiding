from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    service: Literal["api"] = "api"
    mode: Literal["research-paper-only"] = "research-paper-only"


class DependencyStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    postgres: Literal["ok"] = "ok"
    redis: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"] = "ready"
    service: Literal["api"] = "api"
    dependencies: DependencyStatus
