
import sys
from pathlib import Path
from unittest.mock import patch, Mock

import pytest
import requests

# Add assignment_chat directory to Python import path
PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from services.openalex_service import search_research_papers


# -----------------------------
# Mock OpenAlex API response
# -----------------------------

@pytest.fixture
def mock_api_response():
    return {
        "results": [
            {
                "title": "Retrieval-Augmented Generation",
                "publication_year": 2024,
                "authorships": [
                    {
                        "author": {
                            "display_name": "Alice Smith"
                        }
                    },
                    {
                        "author": {
                            "display_name": "Bob Lee"
                        }
                    }
                ],
                "cited_by_count": 120,
                "doi": "https://doi.org/10.1234/example",
                "id": "https://openalex.org/W123"
            },
            {
                "title": "Advances in RAG",
                "publication_year": 2025,
                "authorships": [
                    {
                        "author": {
                            "display_name": "Carol Jones"
                        }
                    }
                ],
                "cited_by_count": 45,
                "doi": None,
                "id": "https://openalex.org/W456"
            }
        ]
    }


# -----------------------------
# Test 1: Successful API search
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_successful_search(mock_get, mock_api_response):

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_api_response
    mock_get.return_value = mock_response

    papers = search_research_papers(
        "retrieval augmented generation",
        2023,
        2025,
        5
    )

    assert len(papers) == 2
    assert papers[0]["title"] == "Retrieval-Augmented Generation"
    assert papers[0]["year"] == 2024
    assert papers[0]["citations"] == 120
    assert papers[0]["authors"] == ["Alice Smith", "Bob Lee"]
    assert papers[1]["doi"] is None

    mock_get.assert_called_once_with(
        "https://api.openalex.org/works",
        params={
            "search": "retrieval augmented generation",
            "filter": "publication_year:2023-2025",
            "per_page": 5
        },
        timeout=20
    )


# -----------------------------
# Test 2: Invalid year range
# -----------------------------

def test_invalid_year_range():

    with pytest.raises(
        ValueError,
        match="start_year cannot be greater than end_year"
    ):
        search_research_papers("AI", 2025, 2023)


# -----------------------------
# Test 3: Invalid result limits
# -----------------------------

@pytest.mark.parametrize("limit", [0, -1, 101, 150])
def test_invalid_max_results(limit):

    with pytest.raises(
        ValueError,
        match="max_results must be between 1 and 100"
    ):
        search_research_papers("AI", 2023, 2025, limit)


# -----------------------------
# Test 4: Empty research topic
# -----------------------------

@pytest.mark.parametrize("topic", ["", "   "])
def test_empty_topic(topic):

    with pytest.raises(
        ValueError,
        match="A research topic is required"
    ):
        search_research_papers(topic, 2023, 2025)


# -----------------------------
# Test 5: Invalid year types
# -----------------------------

def test_invalid_year_types():

    with pytest.raises(
        ValueError,
        match="Publication years must be integers"
    ):
        search_research_papers("AI", "2023", 2025)


# -----------------------------
# Test 6: API timeout
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_api_timeout(mock_get):

    mock_get.side_effect = requests.exceptions.Timeout()

    with pytest.raises(
        RuntimeError,
        match="OpenAlex request timed out"
    ):
        search_research_papers("AI", 2023, 2025)


# -----------------------------
# Test 7: HTTP error
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_http_error(mock_get):

    error_response = Mock()
    error_response.status_code = 429

    mock_get.return_value.raise_for_status.side_effect = (
        requests.exceptions.HTTPError(
            "Too Many Requests",
            response=error_response
        )
    )

    with pytest.raises(
        RuntimeError,
        match="OpenAlex API returned HTTP 429"
    ):
        search_research_papers("AI", 2023, 2025)


# -----------------------------
# Test 8: Network failure
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_network_error(mock_get):

    mock_get.side_effect = requests.exceptions.ConnectionError(
        "Connection failed"
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to connect to OpenAlex"
    ):
        search_research_papers("AI", 2023, 2025)


# -----------------------------
# Test 9: Invalid JSON
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_invalid_json(mock_get):

    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_get.return_value = mock_response

    with pytest.raises(
        RuntimeError,
        match="OpenAlex returned an invalid JSON response"
    ):
        search_research_papers("AI", 2023, 2025)


# -----------------------------
# Test 10: Empty search results
# -----------------------------

@patch("services.openalex_service.requests.get")
def test_empty_results(mock_get):

    mock_response = Mock()
    mock_response.json.return_value = {"results": []}
    mock_get.return_value = mock_response

    papers = search_research_papers("unknown topic", 2023, 2025)

    assert papers == []
