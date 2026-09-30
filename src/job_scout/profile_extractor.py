from pathlib import Path

from langchain_groq import ChatGroq

from . import config
from .cv_reader import read_cv
from .models import Profile
from .prompts import PROFILE_PROMPT


def extract_profile(cv_text: str) -> Profile:
    """Turn raw CV text into a Profile via Groq structured output."""
    llm = ChatGroq(model=config.MODEL_NAME, temperature=0)
    return llm.with_structured_output(Profile).invoke(
        [
            ("system", PROFILE_PROMPT),
            ("human", cv_text),
        ]
    )


if __name__ == "__main__":
    # Project root is two levels above this file: src/job_scout/ -> repo
    cv_path = Path(__file__).resolve().parents[2] / "samples" / "cv.pdf"
    profile = extract_profile(read_cv(cv_path))
    print(profile.model_dump_json(indent=2))
