# My AI Chatbot - Assignment 1

## What is this?
This is a web-based chat app I built using **Gradio** and **LangChain**. It’s hooked up to a GPT-4o-mini model running through an Amazon API Gateway. I’ve tuned the assistant to be witty and helpful, but it has some "no-go" zones to keep the conversation on track.

## What it can do
* **Natural Conversations:** It handles back-and-forth chatting and actually remembers what we talked about earlier in the session.
* **Strict Guardrails:** I’ve programmed the bot to dodge specific topics. It will politely (or wittily) refuse to talk about Pets, Zodiac signs, or Taylor Swift.
* **Secure Connection:** It connects to a cloud-based API Gateway using custom headers to keep the API key safe.

## Behind the Scenes (My Decisions)
1.  **Finding the Secrets:** Pathing can be a headache in Python, so I used an absolute path to the `.secrets` file. This ensures the app finds the API key no matter which folder you launch it from.
2.  **Mapping Messages:** Gradio and LangChain speak different "languages" when it comes to chat history. I wrote a loop to translate Gradio’s history into `HumanMessage` and `AIMessage` objects so the bot doesn't lose its train of thought.
3.  **Keeping it Standard:** I stuck strictly to the libraries provided in the course (LangChain, Gradio, and Dotenv). No extra "fluff" or outside packages were used, making it easy to run on any standard setup.
4.  **Prompt-Based Control:** Instead of writing a bunch of complex "if/else" code to block topics, I used a `SystemMessage`. This sets the bot's "personality" and rules right at the source, making the rejections feel more natural and less like a computer error.