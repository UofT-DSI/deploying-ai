Table of contents

### 0_0 → Prepare and sanitize raw data from sources like Pitchfork.
### 01_1 → Set up environment, API keys, and run basic OpenAI requests.
### 01_2 → Work with context, prompts, and responses from OpenAI and LMStudio.
### 01_3 → Explore local models and test inference on small inputs.
### 02-1 → Convert raw text into numerical representations (vectors) using CountVectorizer and TF-IDF.
### 02-2 → Measure similarity between texts using embeddings and cosine similarity for retrieval.
### 02-3 → Conceptual understanding & local embeddings.
### 02-4 → Generate embeddings for small datasets using OpenAI API.
### 02-5 → Store and query embeddings efficiently with a vector DB (like Chroma).
### 02-6 → Scale the process to large document collections using the Batch API.
### 02-7 → Load batch embeddings into a vector DB (Chroma via Docker) and perform context-aware retrieval for LLM tasks.
### 03-1 → Evaluate model outputs using logprobs to measure confidence and guide decision-making.
### 03-2 → Evaluate RAG outputs by measuring if retrieved documents provide sufficient context.
### 03-3 → Evaluate model outputs using perplexity to measure uncertainty and compare confidence levels.
### 03-4 → Use LLMs as judges (G-Eval / DeepEval) to systematically score outputs on correctness, relevancy, and alignment with context.
### 04-1 → Structure model outputs with Pydantic or TypedDict for downstream processing.
### 05-1 → Extend LLMs with tools using function calling and MCP services.
### 05-2 → Orchestrate LLMs and tools using LangGraph agents to automate multi-step reasoning and dynamically route requests.
### assignment_1 → Evaluate and enhance summaries of documents using structured outputs and DeepEval metrics.

[0_data_pred DB 2 JSON](0_data_prep.ipynb) Prepare and clean raw Pitchfork dataset (18,393 articles) for downstream LLM processing.
    CTA: Convert SQL database tables into structured JSONL files suitable for ingestion by LLMs.
    
    Flow: Connect to SQLite → Sanitize Text → Extract Data from Tables → Convert to JSON Lines → Save to Documents Folder
   
    Challange: 
    Saving json file to SQLite DB (Unable to locate downloaded file)
    Result: @vishnu

[1.1 API, OpenAI Intro and Env Setup](01_1_introduction.ipynb)

    CTA: Set up authentication, environment variables, and verify API access to start querying LLMs.
    
    Flow: Install Packages → Load Environment Variables → Initialize Client → Test API Calls → Confirm Connectivity


[1.2 Context, prompts & Response from OpenAI ](01_2_longer_context.ipynb)

    CTA: Learn how to structure system, user, and assistant prompts to elicit accurate and relevant outputs.
    
    Flow: Define System Context → Craft User Prompts → Send Request → Receive Response → Parse Output

    English: e-book summary to be fetched normally and with input prompt and developer prompt (instruction)

01_3_local_model.ipynb Run LLM locally via LMStudio or equivalent setup without API calls

    CTA: Understand local model deployment, configuration, and inference.
    
    Flow: Setup Local Model → Load Model Weights → Run Inference → Retrieve Outputs → Compare with API Responses

    
02_1_representing_text.ipynb  Convert raw text into numerical representations (vectors)
    
    Techniques Covered:
    CountVectorizer → simple word counts
    TF-IDF → reweighted counts emphasizing rare words

    Output: Document vectors that numerically represent each text.

    Purpose: Set up a numeric representation for downstream tasks like similarity or clustering.

    CTA / v1-style flow:
    Text → Vectorization (Count / TF-IDF) → Document Vectors → Cosine Similarity → Similarity Ranking / Retrieval


02_2_similarity_search.ipynb
    
    Focus: How to use numerical representations (vectors) to measure similarity between texts.
    Goal: Implement similarity search and rank documents by closeness.
    Techniques Covered:
        Cosine similarity
        Identifying the most similar document(s) to a given query
    Output: Similarity scores and ranking of documents based on similarity.
    Purpose: Use vectors (from 02_1) to find “related” or semantically similar texts.
    CTA / v1-style flow:
    Text → Vectorization / Embeddings → Document Vectors → Similarity Metric (Cosine) → Retrieval / Ranking

02_3_embeddings.ipynb “How embeddings are made” (conceptual, deep dive)
 
    Transforming text into contextual embeddings using BERT
    
    Flow: Text → Tokenization → Token IDs → Token Embeddings + Position Embeddings + Token Type Embeddings → Final Contextual Embeddings

    Key point: Unlike simple vectorizations (Count/TF-IDF), embeddings capture semantic meaning and context for each token, enabling tasks like semantic search, clustering, and classification.
        
    Challange: 
   
    Result: @vishnu

02__4_embeddings_api.ipynb “How to use embeddings” (practical, applied)
    Obtaining semantic embeddings via OpenAI’s API
    
    Flow: Text → API Call → Embedding Vectors → Array → Dimensionality Reduction (PCA) → Visualization / Similarity Analysis

    Key point: Using a pre-trained embeddings API allows you to convert text into dense, semantically meaningful vectors directly, enabling similarity measurement, clustering, and downstream tasks without training your own model.

    Challange: 
   
    Result: @vishnu

02_5_vectorDB.ipynb: How to manage embeddings (store, query, search with vector DB).

    CTA: Store, manage, and query text embeddings in a vector database for efficient similarity search and retrieval  
    Flow: Text → Embeddings (OpenAI API) → Vector DB (Chroma) → Document Association → Similarity Query → Top Matches

    Challange: 
   
    Result: @vishnu

02_6_embeddings_at_scale.ipynb > Scale the process to large document collections using the Batch API
    
    CTA: Efficiently generate embeddings for massive datasets without hitting API rate limits  

    Flow: Documents → Text Split → Batch File Preparation → Batch API Upload → Async Embedding Requests → Retrieve Results → Map Text ↔ Embeddings  
    
    Challange: 
   
    Result: @vishnu 


02_7_vectordb_docker.ipynb > Load batch embeddings into a vector DB (Chroma via Docker) and perform context-aware retrieval for LLM tasks

    CTA: Store batch embeddings in a vector DB and perform context-aware retrieval for downstream LLM tasks

    Flow: Batch Embeddings → Map to Original Text → Chroma DB (Docker) → Load Embeddings → Query → Retrieve Context → Generate Prompt → LLM Response  

    Challange: 
   
    Result: @vishnu

03_1_eval_logprobs.ipynb Evaluate model outputs using logprobs to measure confidence and guide decision-making.
    
    CTA: Analyze model confidence, compare token-level probabilities, and improve classification reliability.  
    
    Flow: Text → Completions API → Output Tokens → Logprobs → Top Logprobs → Confidence Assessment → Thresholding / Multi-option Decisions  


03_2_eval_retrieval.ipynb Evaluate RAG outputs by measuring if retrieved documents provide sufficient context.
   
   CTA: Assess the reliability of retrieved documents before generating responses, using logprobs to measure confidence in context coverage.  

    Flow: Query → Document Retrieval → RAG Context → Completions API → Logprobs → Context Sufficiency Check → Thresholding / Decision  

03_3_eval_perplexity.ipynb Evaluate model outputs using perplexity to measure uncertainty and compare confidence levels

    CTA: Assess the uncertainty of model-generated outputs to compare confidence levels across prompts or model runs.  
    
    Flow: Prompt → Completions API → Token Logprobs → Perplexity Calculation → Confidence Assessment → Comparison Across Outputs  

03_4_eval_ai_judge.ipynb Use LLMs as judges (G-Eval / DeepEval) to systematically score outputs on correctness, relevancy, and alignment with context

    CTA: Automate the evaluation of LLM outputs for correctness, relevancy, and alignment with context using metrics like G-Eval and DeepEval.  
    
    Flow: Prompt + LLM Output → Metric Definition (Relevancy, Faithfulness, Correctness) → Test Case Creation → LLM-as-Judge Evaluation → Scoring & Reasoning  

04_1_structured_outputs.ipynb Define and enforce structured output schemas using Pydantic or TypedDict to ensure reliable downstream use of model outputs

    CTA: Ensure model outputs adhere to predefined schemas for safe downstream processing and validation.  
    
    Flow: Prompt → LLM → Structured Output Schema (Pydantic / TypedDict) → Parsed & Validated Output → Downstream Consumption  

05_1_tools.ipynb Extend model capabilities with tools and function calls to dynamically fetch or compute information for enhanced responses.

    CTA: Enable models to call external functions or services to enhance responses, integrate with applications, or fetch dynamic information.  
    
    Flow: User Prompt → LLM detects tool need → Tool Call Generated → Application Executes Function → Output fed back to LLM → Final Response  

05_2_langchain_agent.ipynb Orchestrate LLMs and tools using LangGraph agents to automate multi-step reasoning and dynamically route requests.

    CTA: Build an agent that manages LLM calls, tool invocations, and state to automate multi-step reasoning workflows.  
    
    Flow: Define Tools & Models → Define State → Define Model Node → Define Tool Node → Define Conditional Logic → Build & Compile Agent → Invoke Agent with User Input → Agent Routes Requests and Aggregates Responses  

    English: First we ask a parrot fact to openAI without tool. Then we define tool decorator 

assignment_1.ipynb Evaluate document summaries using structured outputs and DeepEval metrics to automate LLM-based summarization, assessment, and self-correction.
    CTA: Build a workflow that generates structured summaries of documents, evaluates them across multiple metrics, and refines the summary using feedback to improve quality.  

    Flow: Select Document → Load Document Content → Define Structured Output (Pydantic BaseModel) → Generate Summary with LLM → Evaluate Summary using DeepEval (Summarization, Coherence, Tonality, Safety) → Aggregate Scores and Reasons → Enhance Summary using Evaluation Feedback → Re-evaluate and Report Improvements


    Result: @vishnu



        CTA: 
    
    Challange: 
   
    Result: @vishnu 