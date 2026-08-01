from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    """Convert an internal snake_case field name to the public JSON style."""

    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    """Base for strict API contracts with camelCase JSON aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )
