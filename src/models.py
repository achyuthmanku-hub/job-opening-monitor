from dataclasses import dataclass


@dataclass(frozen=True)
class JobPosting:
    company: str
    title: str
    url: str
    source: str
    location: str = ""
    posted_at: str = ""

    @property
    def id(self) -> str:
        return f"{self.source}:{self.url}"
