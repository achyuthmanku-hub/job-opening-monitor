from .base import extract_links_from_html, fetch_html


def fetch_indeed(company: str, source: dict, settings: dict) -> list:
    url = source["url"]
    html = fetch_html(url, settings)
    return extract_links_from_html(
        html,
        base_url=url,
        company=company,
        source=f"indeed:{url}",
        link_selector="a[href*='jk='], a[href*='viewjob'], h2.jobTitle a",
    )
