def parse_chroma_results(results: dict) -> list[dict]:
    """Flatten a ChromaDB query response into a list of dicts.

    Each dict contains all metadata fields plus a 'document' key for the text content.
    """
    return [
        {**dict(results["metadatas"][0][idx]), "document": results["documents"][0][idx]}
        for idx in range(len(results["ids"][0]))
    ]
