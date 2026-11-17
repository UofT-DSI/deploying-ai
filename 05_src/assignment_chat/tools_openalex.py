
from langchain_core.tools import tool
from assignment_chat.services.openalex_service import search_research_papers


@tool
def search_papers(
    topic: str,
    start_year: int,
    end_year: int,
    max_results: int = 5
) -> list[dict]:
    """Search scholarly research papers by topic and year range.

    Use this tool when the user asks to find academic
    publications, authors, citations, or research papers.
    """
    return search_research_papers(
        topic=topic,
        start_year=start_year,
        end_year=end_year,
        max_results=max_results
    )
