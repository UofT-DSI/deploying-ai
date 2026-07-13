# Government Stats Chat Implementation

This chat app builds a graph based on the statistics found on statistics canada https://www150.statcan.gc.ca/

## Three Service Implementations

### Service 1: API


### Service 2: Vector Search

#### Extracting Single File Text Stored in a List

This idea here is to get all the productId from the Statistics Canada website. The JSON response will contain the productId as well as the product description. By embedding the product description, it becomes possible to use RAG to identify which product to use for graph creation. 

#### Batching

At this step, I decided to format my source file in .jsonl and to batches of 150 because otherwise they were too heavy to download through the gateway.

#### Storing Vector
The vector embeddings are stored in /embeddings as well as in a chromadb collection called product_list.


### Service 3: MCP

#### Description

This server provides visual responses to user's queries by fetching statistics on the official canadian government statistics API and returns a graph in the form of python code.

#### Tool Calling
An API call to a Canadian government statistics service is made. The API call is to hhttps://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods and takes two parameters product_id (the topic of the response) and n_lastest (the number of reports that should be included in the response).



## User Interface (Incomplete)

### Bot Personality
Since you are Canadian, your responses must be always well-mannered, uplifting, and overly apologetic. 


## Limitations and Safeguards (Complete)

### Accessing/Revealing Prompt

Do not reveal your internal chain-of-thought or how you used the chunks.
If you are not certain or the information is not available, clearly state that you do not have enough information.


### Modifying System Prompt

Make only minimal modifications to the statistics returned by the API.
Do not add any additional information or embellishments to the statistics.


### Any Mention of Taylor Swift

   Do not, ever, talk or mention Taylor Swift. 
