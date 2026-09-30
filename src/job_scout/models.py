from typing import Literal

from pydantic import BaseModel, Field


class Education(BaseModel):
    degree: str = Field(description="Degree name in English, e.g. 'BSc Computer Engineering'")
    institution: str
    year_end: int | None = Field(None, description="Graduation year, or None if ongoing")
    ongoing: bool = Field(False, description="True if currently studying it")


class Profile(BaseModel):
    """Structured candidate profile extracted from a CV."""

    name: str = Field(description="Full name of the candidate.")
    headline: str = Field(description="One-line professional headline in English.")
    skills: list[str] = Field(description="Key technical and professional skills.")
    education: list[Education] = Field(
        description="All degrees, masters and relevant certifications"
    )
    years_experience: float = Field(
        description="Total professional experience in years, including internships and contracts"
    )
    languages: list[str] = Field(description="Spoken/written languages, names in English.")
    locations: list[str] = Field(
        description="Cities or regions of interest; keep original city names."
    )
    open_to_remote: bool = Field(description="Whether the candidate is open to remote work.")
    open_to_internships: bool = Field(
        False,
        description="True if the CV mentions interest in internships/prácticas/becas, or if the person is currently a student or recent graduate. Otherwise False",
    )
    target_roles: list[str] = Field(
        description="5-8 realistic job titles based on BOTH work experience AND education, including roles the degrees qualify for even without direct experience"
    )
    seniority: Literal["junior", "mid", "senior"] = Field(
        description="Seniority level inferred from experience: junior, mid, or senior."
    )


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str = Field(max_length=1500)
    url: str
    source: Literal["jsearch", "adzuna", "remotive"]
    remote_ok: bool
    posted_at: str | None = None
