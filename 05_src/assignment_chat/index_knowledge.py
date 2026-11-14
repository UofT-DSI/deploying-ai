
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from assignment_chat.services.semantic_search import (
    add_knowledge,
    collection
)

from assignment_chat.data.fitness_knowledge.knowledge_base import (
    FITNESS_DOCUMENTS
)


if collection.count() < len(FITNESS_DOCUMENTS):
    add_knowledge(FITNESS_DOCUMENTS)
    print(f"Successfully indexed {len(FITNESS_DOCUMENTS)} documents.")

else:
    print(f"Knowledge base already contains {collection.count()} documents.")
