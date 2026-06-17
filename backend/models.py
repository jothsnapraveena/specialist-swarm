"""Pydantic request/response shapes for the Recruitment Drive backend."""

from pydantic import BaseModel, Field


class CandidateCreate(BaseModel):
    text: str = Field(min_length=1)


class JobCreate(BaseModel):
    text: str = Field(min_length=1)


class Availability(BaseModel):
    date: str
    slots: int


class Panelist(BaseModel):
    id: str
    name: str
    skills: list[str]
    location: str
    availability: list[Availability]


class PanelistPoolUpdate(BaseModel):
    interview_date: str
    panelist_pool: list[Panelist]


class DriveCreate(BaseModel):
    candidate_id: str
    job_id: str
