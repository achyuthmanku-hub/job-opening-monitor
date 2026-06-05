from .base import extract_links_from_html, fetch_html


def fetch_career_portal(company: str, source: dict, settings: dict) -> list:
    url = source["url"]
    html = fetch_html(url, settings)
    return extract_links_from_html(
        html,
        base_url=url,
        company=company,
        source=f"career_portal:{url}",
    )
