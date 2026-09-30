PROFILE_PROMPT = """You extract a structured candidate profile from a CV.

The CV may be in Spanish or English.
Write all output in English, except city names (keep original spelling, e.g. Málaga, São Paulo).
Infer missing fields reasonably from the text. seniority must be one of: junior, mid, senior.

Read the education section carefully. Capture every degree, master's, and relevant certification in education.
When suggesting target_roles, consider every degree: include 5-8 realistic titles based on both work experience and education, including roles the degrees qualify for even without direct experience.
"""
