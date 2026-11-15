# Assignment 2: Course Chat Sample

This sample is a Gradio conversation with three services. It uses a friendly Toronto voice and passes prior turns to the LangGraph model on each message.

## Run

Use the course environment from the repository root. Set `OPENAI_API_KEY` for the chat model, then run:

```powershell
python 05_src/assignment_chat/app.py
```

The included semantic index is ready to query. No Chroma server, Postgres server, or embedding build step is needed to run the sample. Weather requests need internet access. The model and weather service may incur their respective usage costs or limits.

## Services

1. **Weather API:** `tools_weather.py` requests a location and current conditions from Open-Meteo, then gives the result in the assistant's own words with attribution. Open-Meteo offers a key-free non-commercial API; observe its terms and limits.
2. **Course semantic search:** `tools_course_search.py` searches a committed persistent Chroma index of short sections from the course README, Assignment 2 instructions, and evaluator guide. `build_index.py` explains the indexing process; graders do not need to run it. The index uses TF-IDF followed by latent semantic analysis, with query projection data in `search_model.json`. The included data is below the assignment's 40 MB limit.
3. **Unit conversion:** `tools_conversion.py` exposes Celsius/Fahrenheit and kilometres/miles conversions through function calling.

The graph in `main.py` refuses requests about cats or dogs, horoscopes or Zodiac signs (including “star sign”), and Taylor Swift before calling the model or a tool. `prompts.py` also instructs the model to follow these restrictions and to keep its system instructions private. The gate covers direct mentions of the restricted topics; facilitators should still test evasive wording and prompt injection during their own review.

## Submission

Follow the [Assignment Submission Guide](https://github.com/UofT-DSI/onboarding/blob/main/onboarding_documents/submissions.md) and `02_activities/assignment_2.md`.

- Branch: `assignment-2`.
- Submit the project files for the chat application in the pull request.
- The pull request link should have the form `https://github.com/<your_github_username>/deploying-ai/pull/<pr_id>` and be visible in a private browser window.
