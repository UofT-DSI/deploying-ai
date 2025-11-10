# Assignment 2: A Sample Response

The goal of this assignment is to design and implement an AI system with a conversational interface.

Before you begin, keep in mind that meeting the requirements is important, but more important is that you solve the technical problems associated with the implementation. The assignment is fairly open-ended and can easily become an expansive project. My recommendation is that you implement a simplified version of the services, before moving to more complex implementation. Remember to test your code constantly.  

## Services

This implementation is based on LangGraph's tools. 

The file main.py contains the llm model calls that controls the chat. Tools are in the files tools_*.py.

### Service 1: API Calls

+ There are a few API calls that we implemented throughout the course. They are organized in tools_animals.py and tool_horoscope.py. 
+ Each tool is imported to main and included in the list `tools`.
+ The tools node uses LangGraph's `ToolNode` class and `tools_condition` is the standard tool stopping criteria.
+ All restrictions and tone requirements are in the instructions prompt. You can find this in prompts.py.

### Service 2: Semantic Query

+ This simple implementation is based on our Pitchfork exercise.
+ The tool is also imported from its tools_*.py file.
+ Ensure that the Docker implementation of ChromaDB and Postgres are running.

### Service 3: Your Choice

+ Not implemented

## User Interface

+ Added conversational style.
+ Implemented in Gradio

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
