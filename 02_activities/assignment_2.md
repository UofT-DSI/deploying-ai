# Assignment 2

The goal of this assignment is to design and implement an AI system with a conversational interface.

Before you begin, keep in mind that meeting the requirements is important, but more important is that you solve the technical problems associated with the implementation. The assignment is fairly open-ended and can easily become an expansive project. My recommendation is that you implement a simplified version of the services, before moving to more complex implementation. Remember to test your code constantly.  

# Requirements

Your project should meet the following specifications.

## Services

You must include at least **three services** in your system.

### Service 1: API Calls

* One service must use an API as its back end.
* You can refer to the list of [public and free APIs on GitHub](https://github.com/public-apis/public-apis).
* This service may simply return the API’s output to the user, but the response must not be provided verbatim. Instead, transform or rephrase the output, for example, by summarizing, rewriting in a natural tone, or converting structured data into written text.

### Service 2: Semantic Query

* One service must allow users to ask questions that are resolved through a semantic search (or a hybrid approach, such as lexical search followed by semantic search).
* You may use the datasets introduced in class, or choose your own dataset. 

If you use your own dataset:
* Please **limit file sizes to 40 MB**, so it can be easily shared via GitHub. Note that GitHub warns about files over 50 MB and we generally want to avoid uploading large files.
* **Do not expect us to run the code use to produce embeddings** in the repository. You can include the code used to produce the embeddings, but we ask you to describe your embedding process in the project’s README file.
* Use a [ChromaDB instance with file persistence](https://docs.trychroma.com/docs/run-chroma/persistent-client). This is similar to the first implementation used in class but smaller and easier to host than the Docker-based version.
* If your app needs to access structured data (e.g., to enrich query results), you may use CSV files read with pandas as a back end.
* Please do not use SQLite. We did not include a SQLite library in your environment.

### Service 3: Your Choice

* The third service is open-ended: you may design it as you wish.
* It must make use of one of the following tools:

  * [Function Calling](https://platform.openai.com/docs/guides/function-calling) (API calling is acceptable, but not mandatory)
  * [Web Search](https://platform.openai.com/docs/guides/tools-web-search?api-mode=responses): You may perform simple web searches; if you use **agentic searches**, justify your decision. Avoid using “Deep Research.”
  * [MCP Server Connection](https://platform.openai.com/docs/guides/tools-connectors-mcp): You can explore available servers on [glama.ai](https://glama.ai/mcp/servers).

## User Interface

* The system must include a chat-based interface, preferably implemented with Gradio.
* Give the chat client a distinct personality to make the interaction engaging. For example, assign a specific tone, role, or conversational style.
* The chat interface must maintain memory throughout the conversation.

  * (Optional) Implement a memory management system for long conversations. You don’t need long-term memory, but you should demonstrate how your system handles situations when a conversation becomes too long for the context window.
  * (Optional) You may decide the context window’s size, but remember that full coverage of the entire conversation is not required. A useful reference is ['Manage short-term memory' from LangGraph](https://docs.langchain.com/oss/python/langgraph/add-memory#manage-short-term-memory).

---

## Guardrails and Other Limitations

* Include guardrails that prevent users from:

  * Accessing or revealing the system prompt.
  * Modifying the system prompt directly.

* The model must not respond to questions on certain restricted topics:

  * Cats or dogs
  * Horoscopes or Zodiac Signs
  * Taylor Swift

## Implementation

+ Implement your code in the folder `./05_src/assignment_chat`.
+ Add a `readme.md` where you explain the nature of your chat client, the serivices that it provides, and any decisions that you made related to the implementation.
+ We will not be able to install more libraries to assess your work. Please use the standard setup of the course.

# Submission Information

**Please review our [Assignment Submission Guide](https://github.com/UofT-DSI/onboarding/blob/main/onboarding_documents/submissions.md)** for detailed instructions on how to format, branch, and submit your work. Following these guidelines is crucial for your submissions to be evaluated correctly.

## Submission Parameters

- The Submission Due Date is indicated in the [readme](../README.md#schedule) file.
- The branch name for your repo should be: assignment-1
- What to submit for this assignment:
    + This Jupyter Notebook (assignment_1.ipynb) should be populated and should be the only change in your pull request.
- What the pull request link should look like for this assignment: `https://github.com/<your_github_username>/deploying-ai/pull/<pr_id>`
    + Open a private window in your browser. Copy and paste the link to your pull request into the address bar. Make sure you can see your pull request properly. This helps the technical facilitator and learning support staff review your submission easily.

## Checklist

+ Created a branch with the correct naming convention.
+ Ensured that the repository is public.
+ Reviewed the PR description guidelines and adhered to them.
+ Verify that the link is accessible in a private browser window.

If you encounter any difficulties or have questions, please don't hesitate to reach out to our team via our Slack. Our Technical Facilitators and Learning Support staff are here to help you navigate any challenges.
