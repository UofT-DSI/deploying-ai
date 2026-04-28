"""
Service 2: Semantic Search Service
Uses ChromaDB with file persistence and sentence-transformers embeddings
over a curated dataset of 50 research abstracts spanning key academic fields.
"""

import os
import chromadb
from chromadb.utils import embedding_functions


# ── ChromaDB setup ────────────────────────────────────────────────────────────
DB_PATH        = os.path.join(os.path.dirname(__file__), "../data/chroma_db")
COLLECTION_NAME = "research_abstracts"


def get_collection():
    """Return (or create) the ChromaDB collection."""
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def populate_if_empty():
    """Seed the collection with 50 curated research abstracts if empty."""
    collection = get_collection()
    if collection.count() > 0:
        return  # already populated

    abstracts = [
        # ── Climate & Environment ──────────────────────────────────────────
        ("clim001", "Climate Change and Human Migration",
         "Rising temperatures and extreme weather events are displacing millions globally. "
         "Research indicates that by 2050, up to 216 million people may migrate within their "
         "own countries due to climate impacts, particularly in Sub-Saharan Africa and South Asia."),

        ("clim002", "Ocean Acidification and Marine Biodiversity",
         "Increased CO2 absorption by oceans lowers pH levels, threatening coral reefs and "
         "shellfish populations. Studies show a 26% increase in ocean acidity since pre-industrial "
         "times, with cascading effects on marine food webs."),

        ("clim003", "Renewable Energy Transition Pathways",
         "A comprehensive review of global energy transition strategies finds that solar and wind "
         "capacity must triple by 2030 to meet Paris Agreement targets. Policy incentives and "
         "grid modernization are identified as critical enablers."),

        ("clim004", "Urban Heat Islands and Public Health",
         "Urban areas can be 1–7°C warmer than surrounding rural areas due to heat island effects. "
         "This phenomenon increases heat-related mortality, energy consumption, and air pollution, "
         "disproportionately affecting low-income urban populations."),

        ("clim005", "Permafrost Thaw and Carbon Release",
         "Thawing Arctic permafrost releases stored carbon as CO2 and methane, creating a feedback "
         "loop that accelerates warming. Estimates suggest 1.5 trillion tonnes of carbon are stored "
         "in permafrost, dwarfing current atmospheric levels."),

        # ── Artificial Intelligence & Technology ──────────────────────────
        ("ai001", "Transformer Architectures in Natural Language Processing",
         "The introduction of attention mechanisms and transformer models has revolutionized NLP. "
         "BERT, GPT, and their descendants achieve state-of-the-art performance on tasks ranging "
         "from sentiment analysis to question answering by leveraging large-scale pretraining."),

        ("ai002", "Ethical Implications of Algorithmic Decision-Making",
         "Automated decision systems in hiring, lending, and criminal justice raise concerns about "
         "fairness and accountability. Research highlights how biased training data perpetuates "
         "systemic inequalities, calling for explainability standards and regulatory oversight."),

        ("ai003", "Reinforcement Learning in Robotics",
         "Recent advances in deep reinforcement learning have enabled robots to learn complex "
         "manipulation tasks from minimal human supervision. Sim-to-real transfer techniques "
         "are closing the gap between simulation training and real-world deployment."),

        ("ai004", "Federated Learning for Privacy-Preserving AI",
         "Federated learning allows machine learning models to be trained across decentralized "
         "data sources without sharing raw data. This approach is particularly promising for "
         "healthcare applications where patient privacy is paramount."),

        ("ai005", "Large Language Models and Emergent Capabilities",
         "Scaling language models beyond 100 billion parameters reveals emergent capabilities not "
         "present in smaller models, including multi-step reasoning, code generation, and "
         "few-shot learning across diverse domains."),

        # ── Cognitive Science & Psychology ────────────────────────────────
        ("cog001", "Cognitive Behavioural Therapy for Anxiety Disorders",
         "Meta-analyses confirm CBT as the most evidence-based psychological intervention for "
         "anxiety disorders, with effect sizes of 0.8–1.3. Digital CBT platforms are expanding "
         "access to treatment in underserved populations."),

        ("cog002", "Neuroplasticity and Learning",
         "The brain's ability to reorganize synaptic connections in response to experience "
         "underpins all learning. Research in neuroplasticity shows that spaced repetition, "
         "retrieval practice, and sleep consolidation significantly enhance long-term memory."),

        ("cog003", "The Default Mode Network and Creativity",
         "Neuroimaging studies reveal that the default mode network, active during mind-wandering "
         "and daydreaming, plays a crucial role in creative cognition. High connectivity between "
         "DMN and executive control networks characterizes highly creative individuals."),

        ("cog004", "Sleep Deprivation and Cognitive Performance",
         "Chronic sleep restriction below 6 hours impairs attention, working memory, and "
         "decision-making to an extent comparable to total sleep deprivation. Adolescents "
         "are particularly vulnerable due to delayed circadian rhythms."),

        ("cog005", "Social Media Use and Mental Health",
         "Longitudinal studies present mixed findings on social media and wellbeing. Passive "
         "consumption is associated with increased depression and loneliness, while active "
         "engagement and community-building show neutral or positive effects."),

        # ── Economics & Social Science ────────────────────────────────────
        ("econ001", "Universal Basic Income: Evidence from Pilot Studies",
         "Pilot programs in Finland, Kenya, and Stockton, California show that unconditional "
         "cash transfers improve mental health, increase entrepreneurship, and do not "
         "significantly reduce workforce participation, challenging common assumptions."),

        ("econ002", "The Gig Economy and Worker Precarity",
         "Platform-based work offers flexibility but reduces job security, benefits, and "
         "collective bargaining power. Research documents rising income volatility among "
         "gig workers, with significant implications for social safety net design."),

        ("econ003", "Behavioural Economics and Nudge Theory",
         "Drawing on cognitive biases, nudge theory designs choice architectures that steer "
         "individuals toward beneficial decisions without restricting freedom. Applications "
         "span retirement savings, organ donation, and energy conservation."),

        ("econ004", "Inequality and Economic Mobility",
         "Cross-national comparisons reveal that countries with higher income inequality "
         "exhibit lower intergenerational economic mobility, a finding known as the Great Gatsby "
         "Curve. Education access and early childhood investment are key equalizing factors."),

        ("econ005", "Cryptocurrency and Financial Stability",
         "The rapid growth of decentralized finance raises questions about systemic risk, "
         "investor protection, and monetary policy transmission. Central bank digital currencies "
         "are emerging as regulated alternatives to private cryptocurrencies."),

        # ── Medicine & Public Health ──────────────────────────────────────
        ("med001", "CRISPR-Cas9 and Therapeutic Gene Editing",
         "CRISPR-Cas9 enables precise editing of the human genome, offering potential cures "
         "for sickle cell disease, beta-thalassemia, and inherited blindness. Clinical trials "
         "show promising early results, though off-target effects remain a concern."),

        ("med002", "Antibiotic Resistance: A Global Health Crisis",
         "Antimicrobial resistance is projected to cause 10 million deaths annually by 2050 "
         "if unchecked. Overuse in agriculture and healthcare drives resistance development, "
         "while the drug development pipeline for new antibiotics remains critically thin."),

        ("med003", "The Gut Microbiome and Mental Health",
         "The gut-brain axis mediates bidirectional communication between intestinal microbiota "
         "and the central nervous system. Research links microbiome diversity to mood regulation, "
         "with implications for treating depression through dietary and probiotic interventions."),

        ("med004", "Vaccine Hesitancy and Public Health",
         "Vaccine hesitancy threatens herd immunity for preventable diseases. Studies identify "
         "misinformation, distrust of institutions, and complacency as primary drivers, "
         "with tailored community engagement proving most effective in increasing uptake."),

        ("med005", "Precision Medicine and Genomic Profiling",
         "Advances in genomic sequencing enable treatment strategies tailored to individual "
         "genetic profiles. Oncology leads adoption, with targeted therapies improving outcomes "
         "in lung, breast, and colorectal cancers beyond standard chemotherapy."),

        # ── Education Research ────────────────────────────────────────────
        ("edu001", "Active Learning and Student Outcomes",
         "Meta-analyses of over 225 studies find that active learning strategies — including "
         "problem-based learning, peer instruction, and flipped classrooms — improve exam "
         "performance by 6% and reduce failure rates by 1.5x compared to traditional lecturing."),

        ("edu002", "The Achievement Gap and Socioeconomic Status",
         "Persistent gaps in academic achievement between high- and low-income students reflect "
         "differential access to resources, experienced teachers, and enriching environments. "
         "Early childhood education programs show the highest return on investment for closing gaps."),

        ("edu003", "Online Learning Effectiveness",
         "Systematic reviews find that online learning is as effective as face-to-face instruction "
         "for most outcomes when well-designed. Hybrid models combining online flexibility with "
         "in-person interaction show superior results for complex skill development."),

        ("edu004", "Growth Mindset Interventions",
         "Carol Dweck's growth mindset research demonstrates that students who believe intelligence "
         "is malleable achieve higher academic outcomes. Brief online interventions shift mindset "
         "and improve grades, particularly for struggling students."),

        ("edu005", "Teacher Quality and Student Achievement",
         "Research consistently finds teacher effectiveness to be the most influential "
         "school-based factor in student achievement, exceeding the impact of class size, "
         "technology, or curriculum. Mentoring and reflective practice drive teacher development."),

        # ── Physics & Cosmology ───────────────────────────────────────────
        ("phys001", "Dark Matter: Evidence and Candidate Particles",
         "Gravitational lensing, galaxy rotation curves, and CMB observations confirm that "
         "dark matter constitutes 27% of the universe's energy density. WIMPs, axions, and "
         "sterile neutrinos remain leading particle candidates despite null direct detection results."),

        ("phys002", "Quantum Entanglement and Information Theory",
         "Quantum entanglement enables correlations between particles regardless of distance, "
         "underpinning quantum cryptography and teleportation protocols. Bell test experiments "
         "have definitively ruled out local hidden variable theories."),

        ("phys003", "Gravitational Waves and Multi-Messenger Astronomy",
         "LIGO's detection of gravitational waves from binary black hole mergers opened a new "
         "observational window on the universe. The neutron star merger GW170817 provided "
         "the first multi-messenger event combining gravitational and electromagnetic signals."),

        ("phys004", "The Standard Model and Beyond",
         "The Standard Model successfully describes three of four fundamental forces and "
         "predicts particle properties with extraordinary precision. However, it cannot "
         "account for gravity, dark matter, or the matter-antimatter asymmetry of the universe."),

        ("phys005", "Black Hole Information Paradox",
         "Hawking radiation implies black holes eventually evaporate, raising the question "
         "of whether information is destroyed — violating quantum mechanics. Recent work "
         "on the Page curve and island formula suggests information is preserved, but the "
         "mechanism remains debated."),

        # ── History & Humanities ──────────────────────────────────────────
        ("hist001", "The Scientific Revolution and Modern Epistemology",
         "The 16th–17th century Scientific Revolution replaced Aristotelian natural philosophy "
         "with empirical observation and mathematical modelling. Copernicus, Galileo, and Newton "
         "established a framework that underpins modern science and shaped Enlightenment thought."),

        ("hist002", "Colonialism and Its Long-Term Economic Effects",
         "Econometric studies find that colonial institutions and resource extraction strategies "
         "have persistent negative effects on post-colonial economic development. Countries with "
         "more extractive colonial histories exhibit higher inequality and weaker institutions today."),

        ("hist003", "The Printing Press and the Spread of Ideas",
         "Gutenberg's printing press enabled rapid dissemination of texts, fuelling the "
         "Reformation, the Scientific Revolution, and the Enlightenment. Historians debate "
         "whether it democratized knowledge or primarily empowered those already literate."),

        ("hist004", "Oral Histories and Marginalized Voices",
         "Oral history methodology recovers perspectives absent from official archives, "
         "particularly those of women, indigenous peoples, and working classes. Digital "
         "archiving is expanding access to and preservation of oral testimony collections."),

        ("hist005", "The Silk Road and Cross-Cultural Exchange",
         "The Silk Road facilitated not only trade in goods but also the transmission of "
         "religions, technologies, diseases, and artistic styles across Eurasia. Recent "
         "archaeology reveals its network was far more complex than a single route."),

        # ── Sociology & Anthropology ──────────────────────────────────────
        ("soc001", "Intersectionality and Social Inequality",
         "Kimberlé Crenshaw's intersectionality framework examines how overlapping social "
         "identities — race, gender, class, sexuality — create unique patterns of discrimination "
         "and privilege. It has become foundational in feminist theory and social policy analysis."),

        ("soc002", "Urbanization and Social Cohesion",
         "Rapid urbanization strains social infrastructure and can erode community ties. "
         "Research finds that mixed-use neighbourhoods, public spaces, and participatory "
         "governance foster social cohesion in growing cities."),

        ("soc003", "Cultural Evolution and Meme Theory",
         "Dawkins' concept of memes — units of cultural transmission — frames cultural "
         "evolution as analogous to biological evolution. Quantitative cultural evolution "
         "research uses large text corpora to track how ideas spread and mutate over time."),

        ("soc004", "Migration, Identity, and Integration",
         "Studies of immigrant integration show that second-generation migrants often "
         "navigate hybrid identities. Structural factors — labour market access, language "
         "acquisition support, and anti-discrimination policy — outweigh cultural factors "
         "in predicting long-term integration outcomes."),

        ("soc005", "The Sociology of Scientific Knowledge",
         "Science and Technology Studies examines how social, political, and cultural factors "
         "shape scientific knowledge production. Laboratory studies reveal science as a "
         "social practice, challenging naive views of purely objective inquiry."),

        # ── Environmental Science ─────────────────────────────────────────
        ("env001", "Biodiversity Loss and Ecosystem Services",
         "The current rate of species extinction is estimated at 100–1,000 times the "
         "natural background rate, constituting a sixth mass extinction. Biodiversity loss "
         "undermines ecosystem services — pollination, water purification, carbon sequestration — "
         "valued at trillions of dollars annually."),

        ("env002", "Microplastics in Marine and Freshwater Systems",
         "Microplastic contamination is now detected in the deepest ocean trenches, Arctic "
         "ice, and human blood. Research documents impacts on marine invertebrates, fish "
         "reproductive systems, and potential human health effects through food chain accumulation."),

        ("env003", "Rewilding and Ecosystem Restoration",
         "Rewilding — reintroducing apex predators and restoring natural processes — has "
         "produced dramatic ecosystem recoveries. The reintroduction of wolves to Yellowstone "
         "cascaded through trophic levels, restoring vegetation and stream morphology."),

        ("env004", "Water Scarcity and Conflict",
         "By 2025, two-thirds of the world population may face water stress. Research "
         "identifies shared river basins as potential flashpoints for conflict, while "
         "cooperative water treaties have historically reduced interstate tensions."),

        ("env005", "The Circular Economy and Waste Reduction",
         "Moving from a linear 'take-make-dispose' model to circular production and "
         "consumption could reduce global resource use by 32% by 2030. Extended producer "
         "responsibility policies are among the most effective regulatory instruments."),
    ]

    ids      = [a[0] for a in abstracts]
    metadata = [{"title": a[1]} for a in abstracts]
    docs     = [a[2] for a in abstracts]

    collection.add(documents=docs, ids=ids, metadatas=metadata)
    print(f"[semantic_service] Seeded {len(abstracts)} abstracts into ChromaDB.")


def semantic_search(query: str, n_results: int = 3) -> str:
    """
    Perform semantic search over the research abstracts collection.
    Returns a formatted string of the top matching abstracts.
    """
    try:
        populate_if_empty()
        collection = get_collection()

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        docs      = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        if not docs:
            return "No relevant research abstracts found."

        output = []
        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances)):
            similarity = round((1 - dist) * 100, 1)
            output.append(
                f"[Result {i+1}] {meta.get('title', 'Untitled')} "
                f"(Relevance: {similarity}%)\n{doc}"
            )

        return "\n\n".join(output)

    except Exception as e:
        return f"Semantic search encountered an error: {str(e)}"
