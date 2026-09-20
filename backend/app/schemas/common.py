"""Success envelope: every successful response is {"data": ..., "meta": ...}."""

from pydantic import BaseModel


class Meta(BaseModel):
    request_id: str


class SuccessEnvelope[T](BaseModel):
    data: T
    meta: Meta
