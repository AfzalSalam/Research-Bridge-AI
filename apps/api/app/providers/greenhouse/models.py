from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

BoundedTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
BoundedContent = Annotated[str, StringConstraints(max_length=250_000)]


class GreenhouseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GreenhouseLocation(GreenhouseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class GreenhouseDepartment(GreenhouseModel):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
    ]


class GreenhouseJob(GreenhouseModel):
    id: int = Field(ge=1)
    title: BoundedTitle
    updated_at: datetime
    location: GreenhouseLocation = Field(default_factory=GreenhouseLocation)
    absolute_url: HttpUrl
    content: BoundedContent = ""
    departments: list[GreenhouseDepartment] = Field(default_factory=list, max_length=30)


class GreenhouseEnvelope(GreenhouseModel):
    jobs: list[dict[str, Any]] = Field(max_length=1_000)
