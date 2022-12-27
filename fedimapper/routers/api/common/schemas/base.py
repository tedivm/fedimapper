from datetime import datetime

from pydantic import BaseModel, Field


class ResponseBase(BaseModel):
    class Config:
        allow_mutation = False
        extra = "forbid"
        orm_mode = True

    generated_at: datetime = Field(default_factory=datetime.utcnow)
