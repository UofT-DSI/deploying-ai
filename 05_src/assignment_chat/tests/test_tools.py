import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from assignment_chat.tools_conversion import convert_units
from assignment_chat.tools_course_search import search_course_materials
from assignment_chat.tools_weather import get_weather


class SampleToolsTests(unittest.TestCase):
    def test_conversion_is_a_distinct_function_call(self):
        self.assertIn("32.00 fahrenheit", convert_units.invoke({
            "value": 0, "from_unit": "celsius", "to_unit": "fahrenheit"}))

    def test_course_search_uses_committed_index(self):
        result = search_course_materials.invoke({"question": "What branch submits Assignment 2?"})
        self.assertIn("assignment_2.md", result)
        self.assertIn("assignment-2", result)

    def test_weather_rephrases_api_result(self):
        places = Mock()
        places.json.return_value = {"results": [{"name": "Toronto", "latitude": 43.7, "longitude": -79.4}]}
        forecast = Mock()
        forecast.json.return_value = {"current": {"temperature_2m": 10, "wind_speed_10m": 5}}
        with patch("assignment_chat.tools_weather.requests.get", side_effect=[places, forecast]):
            result = get_weather.invoke({"city": "Toronto"})
        self.assertIn("10", result)
        self.assertIn("Toronto", result)
        self.assertIn("Open-Meteo", result)


if __name__ == "__main__":
    unittest.main()
