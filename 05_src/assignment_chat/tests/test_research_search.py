
"""Unit tests for ResearchMate AI semantic search."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR.parent))

from assignment_chat.build_index import chunk_text
from assignment_chat.tools_research_search import retrieve_passages


def test_chunk_text_with_overlap():
    text = "abcdefghij"

    chunks = chunk_text(
        text,
        chunk_size=6,
        overlap=2,
    )

    assert chunks == ["abcdef", "efghij"]


def test_empty_text():
    assert chunk_text("") == []


def test_invalid_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("example", chunk_size=0)


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("example", chunk_size=5, overlap=5)


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_invalid_top_k(top_k):
    with pytest.raises(ValueError):
        retrieve_passages("What is RAG?", top_k=top_k)


def test_empty_question():
    with pytest.raises(ValueError):
        retrieve_passages("   ")


@patch("assignment_chat.tools_research_search.OpenAI")
@patch("assignment_chat.tools_research_search.get_collection")
@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_successful_retrieval(mock_collection, mock_openai):
    collection = MagicMock()
    collection.count.return_value = 2

    collection.query.return_value = {
        "documents": [[
            "RAG combines retrieval and generation."
        ]],
        "metadatas": [[{
            "title": "RAG Paper",
            "arxiv_id": "2005.11401",
            "page": 1,
            "source": "https://arxiv.org/abs/2005.11401",
        }]],
        "distances": [[0.12]],
    }

    mock_collection.return_value = collection

    mock_client = mock_openai.return_value
    mock_client.embeddings.create.return_value = (
        SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2, 0.3])
            ]
        )
    )

    results = retrieve_passages(
        "Explain RAG",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0]["title"] == "RAG Paper"
    assert results[0]["page"] == 1
    assert results[0]["distance"] == 0.12

    collection.query.assert_called_once()
    assert collection.query.call_args.kwargs["n_results"] == 1


@patch("assignment_chat.tools_research_search.OpenAI")
@patch("assignment_chat.tools_research_search.get_collection")
@patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
def test_empty_collection(mock_collection, mock_openai):
    collection = MagicMock()
    collection.count.return_value = 0
    mock_collection.return_value = collection

    assert retrieve_passages("Explain transformers") == []
    mock_openai.assert_not_called()
