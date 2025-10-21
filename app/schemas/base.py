# app/schemas/base.py
try:
    # Pydantic v2
    from pydantic import BaseModel, ConfigDict
    def to_camel(s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])
    class BaseSchema(BaseModel):
        model_config = ConfigDict(
            alias_generator=to_camel,
            populate_by_name=True,
            from_attributes=True,
            str_strip_whitespace=True,
        )
except Exception:
    # Pydantic v1 fallback (혹시 모를 호환용)
    from pydantic import BaseModel
    def to_camel(s: str) -> str:
        parts = s.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])
    class BaseSchema(BaseModel):
        class Config:
            alias_generator = to_camel
            allow_population_by_field_name = True
            orm_mode = True
