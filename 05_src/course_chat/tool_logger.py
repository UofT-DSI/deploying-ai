from langchain_core.callbacks import BaseCallbackHandler
from utils.logger import get_logger

_logs = get_logger(__name__)


class ToolCallLogger(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        _logs.info("tool_call: %s", serialized.get("name", "unknown"))
