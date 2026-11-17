
from pathlib import Path
import chromadb

# Save the knowledge database inside the assignment folder.
DB_PATH = Path(__file__).resolve().parent / "chroma_db"

# Create a persistent ChromaDB database.
client = chromadb.PersistentClient(path=str(DB_PATH))

# Create or open the scientific knowledge collection.
collection = client.get_or_create_collection(
    name="food_protein_knowledge"
)

# Scientific knowledge for ProtinGPT.
knowledge_documents = [
    "Proteins are made of amino acids linked by peptide bonds. "
    "They are important for growth, tissue repair, and enzyme function.",

    "There are nine essential amino acids that adults must obtain "
    "through their diet because the body cannot synthesize them "
    "in sufficient amounts.",

    "Whey protein is a milk-derived protein containing all nine "
    "essential amino acids. It is generally digested relatively quickly.",

    "Soy protein is a plant-based complete protein containing "
    "all nine essential amino acids.",

    "Bioactive peptides are short amino acid sequences that may "
    "have biological activities after being released from proteins. "
    "Some are studied for antioxidant or blood-pressure-related effects.",

    "Protein hydrolysis breaks larger proteins into smaller "
    "peptides and amino acids, often using enzymes.",

    "Protein digestibility describes how effectively dietary "
    "protein can be broken down and its amino acids absorbed."
]

# Give every document a unique identifier.
document_ids = [
    f"protein_doc_{i}" for i in range(len(knowledge_documents))
]
# Store the scientific documents in ChromaDB.
collection.upsert(
    ids=document_ids,
    documents=knowledge_documents
)

print(f"Successfully stored {collection.count()} scientific documents!")

# Test semantic search.
results = collection.query(
    query_texts=["What are bioactive peptides?"],
    n_results=2
)

print("\nSemantic search results:")
for document in results["documents"][0]:
    print("-", document)

# Service 2: Semantic search for scientific knowledge.
def search_protein_knowledge(question):
    results = collection.query(
        query_texts=[question],
        n_results=2
    )

    documents = results["documents"][0]

    return "\n".join(documents)

