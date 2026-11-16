from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FieldName = Literal["age", "education_level", "marks", "annual_income", "category", "application_date", "documents"]
Operator = Literal["between", "min", "max", "in", "by", "all_of", "at_least"]
RuleStatus = Literal["accepted", "pending", "rejected"]


class ApplicantDetails(BaseModel):
    date_of_birth: date | None = None
    education_level: Literal["class10", "class12", "diploma", "bachelor", "master", "doctorate"] | None = None
    marks: float | None = Field(default=None, ge=0, le=100)
    annual_income: float | None = Field(default=None, ge=0, le=1_000_000_000)
    category: Literal["General", "OBC", "SC", "ST", "EWS", "Other"] | None = None
    application_date: date | None = None
    documents: list[str] | None = None

    @field_validator("documents")
    @classmethod
    def clean_docs(cls, value):
        if value is None:
            return value
        if len(value) > 40:
            raise ValueError("Maximum 40 documents")
        return sorted(set(s.strip().lower() for s in value if s.strip()))


class ApplicantInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    details: ApplicantDetails


class ApplicantOut(ApplicantInput):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RuleInput(BaseModel):
    field: FieldName
    operator: Operator
    value: dict
    evidence_text: str = Field(min_length=5, max_length=5000)
    status: RuleStatus = "accepted"
    reviewer_note: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def valid_shape(self):
        expected = {
            "age": "between", "education_level": "at_least", "marks": ("min", "max"),
            "annual_income": ("min", "max"), "category": "in", "application_date": "by", "documents": "all_of"
        }
        ops = expected[self.field]
        if self.operator not in (ops if isinstance(ops, tuple) else (ops,)):
            raise ValueError(f"Operator {self.operator} is invalid for {self.field}")
        keys = {
            "age": ("min", "max", "as_of"), "education_level": ("level",),
            "marks": ("number",), "annual_income": ("number",),
            "category": ("items",), "application_date": ("date",), "documents": ("items",)
        }
        if any(k not in self.value for k in keys[self.field]):
            raise ValueError("Missing required value keys")
        if self.field in ("marks", "annual_income"):
            num = self.value["number"]
            if not isinstance(num, (int, float)) or isinstance(num, bool) or num < 0 or (self.field == "marks" and num > 100):
                raise ValueError("Invalid numeric threshold")
        if self.field == "age":
            for k in ("min", "max"):
                if not isinstance(self.value[k], int) or isinstance(self.value[k], bool) or not 0 <= self.value[k] <= 120:
                    raise ValueError("Age bounds must be integers 0-120")
            if self.value["min"] > self.value["max"]:
                raise ValueError("Invalid age range")
            if self.value["as_of"] is not None:
                date.fromisoformat(str(self.value["as_of"]))
        if self.field == "education_level" and self.value["level"] not in ("class10", "class12", "diploma", "bachelor", "master", "doctorate"):
            raise ValueError("Unknown education level")
        if self.field == "application_date":
            date.fromisoformat(str(self.value["date"]))
        if self.field in ("documents", "category"):
            items = self.value["items"]
            if not isinstance(items, list) or not items or len(items) > 40 or not all(isinstance(x, str) and 0 < len(x) <= 120 for x in items):
                raise ValueError("items must be a nonempty list of short strings")
            if self.field == "category" and any(x not in ("General", "OBC", "SC", "ST", "EWS", "Other") for x in items):
                raise ValueError("Invalid category")
        return self


class RulePatch(RuleInput):
    pass


class SimulationInput(BaseModel):
    old_version_id: int = Field(gt=0)
    new_version_id: int = Field(gt=0)
    applicant_id: int = Field(gt=0)
