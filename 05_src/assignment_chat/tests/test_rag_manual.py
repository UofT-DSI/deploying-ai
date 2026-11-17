
from assignment_chat.tools_research_search import (
    retrieve_passages
)

question = (
    "How does Retrieval-Augmented Generation "
    "combine retrieval and language generation?"
)

results = retrieve_passages(
    question=question,
    top_k=4,
)

print(f"Found {len(results)} passages\n")

for index, passage in enumerate(results, start=1):
    print(f"Result {index}")
    print("Title:", passage["title"])
    print("Page:", passage["page"])
    print("Source:", passage["source"])
    print("Distance:", passage["distance"])
    print("Text:", passage["text"][:500])
    print("-" * 60)
