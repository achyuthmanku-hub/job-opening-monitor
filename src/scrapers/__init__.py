from .amazon import fetch_amazon
from .ashby import fetch_ashby
from .career_portal import fetch_career_portal
from .glassdoor import fetch_glassdoor
from .greenhouse import fetch_greenhouse
from .indeed import fetch_indeed
from .lever import fetch_lever
from .linkedin import fetch_linkedin
from .oracle import fetch_oracle
from .smartrecruiters import fetch_smartrecruiters
from .workday import fetch_workday

SCRAPERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "workday": fetch_workday,
    "oracle": fetch_oracle,
    "amazon": fetch_amazon,
    "smartrecruiters": fetch_smartrecruiters,
    "career_portal": fetch_career_portal,
    "linkedin": fetch_linkedin,
    "indeed": fetch_indeed,
    "glassdoor": fetch_glassdoor,
}
