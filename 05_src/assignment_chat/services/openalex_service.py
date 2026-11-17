import requests

url = "https://api.openalex.org/works"


def search_research_papers(
    topic: str,
    start_year: int,
    end_year: int,
    max_results: int = 5
) -> list[dict]:
    """Search OpenAlex for scholarly research papers."""

    # 1. Input validation
    if not isinstance(start_year, int) or not isinstance(end_year, int):
        raise ValueError("Publication years must be integers.")

    if start_year > end_year:
        raise ValueError("start_year cannot be greater than end_year.")

    if not isinstance(max_results, int) or not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100.")

    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("A research topic is required.")

    # 2. Prepare API request
    params = {
        "search": topic.strip(),
        "filter": f"publication_year:{start_year}-{end_year}",
        "per_page": max_results
    }

    # 3. API error handling
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        raise RuntimeError(
            "OpenAlex request timed out. Please try again."
        ) from None

    except requests.exceptions.HTTPError as error:
        status = error.response.status_code

        raise RuntimeError(
            f"OpenAlex API returned HTTP {status}."
        ) from error

    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            f"Unable to connect to OpenAlex: {error}"
        ) from error

    except ValueError as error:
        raise RuntimeError(
            "OpenAlex returned an invalid JSON response."
        ) from error

    # 4. Process research papers
    papers = []

    for item in data.get("results", []):
        authors = [
            author["author"]["display_name"]
            for author in item.get("authorships", [])
            if author.get("author")
            and author["author"].get("display_name")
        ]

        paper = {
            "title": item.get("title"),
            "year": item.get("publication_year"),
            "authors": authors,
            "citations": item.get("cited_by_count", 0),
            "doi": item.get("doi"),
            "openalex_id": item.get("id")
        }

        papers.append(paper)

    return papers


    