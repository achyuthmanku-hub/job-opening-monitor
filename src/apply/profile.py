from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ApplicationProfile:
    first_name: str
    last_name: str
    email: str
    phone: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str
    linkedin_url: str
    needs_sponsorship: bool
    experience: List[dict[str, Any]] = field(default_factory=list)
    education: List[dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def full_address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"


def load_application_profile(data: dict) -> ApplicationProfile:
    legal = data.get("legal_name", {})
    address = data.get("address", {})
    return ApplicationProfile(
        first_name=str(legal.get("first_name", "")).strip(),
        last_name=str(legal.get("last_name", "")).strip(),
        email=str(data.get("email", "")).strip(),
        phone=str(data.get("phone", "")).strip(),
        street=str(address.get("street", "")).strip(),
        city=str(address.get("city", "")).strip(),
        state=str(address.get("state", "")).strip(),
        zip_code=str(address.get("zip", "")).strip(),
        country=str(address.get("country", "United States")).strip(),
        linkedin_url=str(data.get("linkedin_url", "")).strip(),
        needs_sponsorship=bool(data.get("needs_sponsorship", False)),
        experience=list(data.get("experience", [])),
        education=list(data.get("education", [])),
        certifications=list(data.get("certifications", [])),
    )
