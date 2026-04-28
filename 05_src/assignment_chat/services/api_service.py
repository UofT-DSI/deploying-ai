"""
Service 1: API Service — Open Library
Searches the Open Library API for books and authors.
Returns a structured summary for the assistant to rephrase.
"""

import requests
import json


OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_AUTHOR_URL = "https://openlibrary.org/search/authors.json"


def search_books(query: str, limit: int = 5) -> str:
    """
    Search Open Library for books matching the query.
    Returns a formatted string summary (not verbatim API output).
    """
    try:
        params = {
            "q": query,
            "limit": limit,
            "fields": "title,author_name,first_publish_year,subject,number_of_pages_median"
        }
        response = requests.get(OPEN_LIBRARY_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        if not docs:
            return f"No books found for query: {query}"

        results = []
        for doc in docs:
            title   = doc.get("title", "Unknown Title")
            authors = ", ".join(doc.get("author_name", ["Unknown Author"]))
            year    = doc.get("first_publish_year", "Unknown Year")
            pages   = doc.get("number_of_pages_median", "Unknown")
            subjects = doc.get("subject", [])[:3]  # top 3 subjects
            subject_str = ", ".join(subjects) if subjects else "General"

            results.append(
                f"- Title: {title}\n"
                f"  Author(s): {authors}\n"
                f"  First Published: {year}\n"
                f"  Approx. Pages: {pages}\n"
                f"  Subjects: {subject_str}"
            )

        total = data.get("numFound", 0)
        summary = f"Found {total} total results. Top {len(results)} shown:\n\n"
        summary += "\n\n".join(results)
        return summary

    except requests.exceptions.RequestException as e:
        return f"Book search unavailable at this time: {str(e)}"
    except Exception as e:
        return f"An error occurred during book search: {str(e)}"


def search_author(author_name: str) -> str:
    """
    Search Open Library for an author by name.
    Returns a formatted summary of the author.
    """
    try:
        params = {"q": author_name, "limit": 3}
        response = requests.get(OPEN_LIBRARY_AUTHOR_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        docs = data.get("docs", [])
        if not docs:
            return f"No author found for: {author_name}"

        author = docs[0]
        name         = author.get("name", "Unknown")
        birth_date   = author.get("birth_date", "Unknown")
        top_work     = author.get("top_work", "Unknown")
        work_count   = author.get("work_count", "Unknown")

        return (
            f"Author: {name}\n"
            f"Birth Date: {birth_date}\n"
            f"Most Notable Work: {top_work}\n"
            f"Total Works in Open Library: {work_count}"
        )

    except requests.exceptions.RequestException as e:
        return f"Author search unavailable: {str(e)}"
    except Exception as e:
        return f"An error occurred during author search: {str(e)}"
