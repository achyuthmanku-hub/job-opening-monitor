from .amazon import fetch_amazon
from .ashby import fetch_ashby
from .career_portal import fetch_career_portal
from .glassdoor import fetch_glassdoor
from .greenhouse import fetch_greenhouse
from .indeed import fetch_indeed
from .lever import fetch_lever
from .linkedin import fetch_linkedin
from .oracle import fetch_oracle
from .registry import SCRAPERS, load_plugins, register_scraper
from .smartrecruiters import fetch_smartrecruiters
from .workday import fetch_workday

register_scraper("greenhouse", fetch_greenhouse)
register_scraper("lever", fetch_lever)
register_scraper("ashby", fetch_ashby)
register_scraper("workday", fetch_workday)
register_scraper("oracle", fetch_oracle)
register_scraper("amazon", fetch_amazon)
register_scraper("smartrecruiters", fetch_smartrecruiters)
register_scraper("career_portal", fetch_career_portal)
register_scraper("linkedin", fetch_linkedin)
register_scraper("indeed", fetch_indeed)
register_scraper("glassdoor", fetch_glassdoor)

load_plugins()

__all__ = ["SCRAPERS", "register_scraper", "load_plugins"]
