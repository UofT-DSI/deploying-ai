import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from assignment_chat import app, main
from langchain_core.messages import AIMessage, HumanMessage


class SampleAppTests(unittest.TestCase):
    def test_history_reaches_assignment_graph(self):
        seen = []

        class Graph:
            def invoke(self, state):
                seen.append(state)
                return {"messages": state["messages"] + [AIMessage(content="answer")]}

        with patch.object(app, "graph", return_value=Graph()):
            answer = app.assignment_chat("second question", [
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
            ])
        self.assertEqual(answer, "answer")
        self.assertEqual([message.content for message in seen[0]["messages"]],
                         ["first question", "first answer", "second question"])

    def test_restricted_topics_are_refused_before_model_call(self):
        for question in ("Tell me about cats", "What's my horoscope?", "What's my star sign?", "Who is Taylor Swift?"):
            with self.subTest(question=question), patch.object(main, "init_chat_model") as model:
                graph = main.get_graph()
                reply = graph.invoke({"messages": [HumanMessage(content=question)]})
                self.assertEqual(reply["messages"][-1].content, main.REFUSAL)
                model.return_value.bind_tools.assert_not_called()


if __name__ == "__main__":
    unittest.main()
