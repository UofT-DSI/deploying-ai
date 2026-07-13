import sys
sys.path.append('../05_src/')

import socket
import urllib3.util.connection as urllib3_cn

def force_ipv4():
    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

force_ipv4()

from pydantic import BaseModel, Field
from typing import List, Dict
from dotenv import load_dotenv
from langchain.tools import tool
from utils.clients import get_client
from requests.adapters import HTTPAdapter, Retry

import os
import requests
import json

load_dotenv("../05_src/.env")
load_dotenv("../05_src/.secrets")


MODEL = os.getenv("MODEL")
CHROMA_URL = os.getenv("CHROMA_URL")
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')


client = get_client(use_gateway=True)


from fastmcp import FastMCP

mcp = FastMCP(
    name="can_gov_server",
    instructions="""
    This server provides visual responses to user's queries by fetching statistics on the official canadian government statistics API and returns a graph in the form of python code. 
    """
)


session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "close"
})


@mcp.tool
def get_stats_from_govcan(product_id=35100003, n_latest=25):
    """
    An API call to a Canadian government statistics service is made.
    The API call is to hhttps://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods
    and takes two parameters product_id (the topic of the response) and n_lastest (the number of reports that should be included in the response).
    Accepted values for product_id are: 8-10 digits
    Accepted values for n_latest are: 0-1000.
    """
    res = get_data_from_service(product_id, n_latest)
    data = get_data_from_response(res)
    return data


def get_data_from_service(product_id, n_latest):
    endpoint_api_url = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"
    params = [{
        "productId": product_id,
        "coordinate": "1.12.0.0.0.0.0.0.0.0",
        "latestN": n_latest
    }]

    response = session.post(endpoint_api_url, json=params, timeout=30)
    return response


def get_data_from_response(response) -> Dict[str, List]:
    vector = json.loads(response.text)

    x_data = []
    y_data = []

    points = vector[0]["object"]["vectorDataPoint"]

    for point in points:
        x_data.append(point["refPer2"])
        y_data.append(point["value"])

    return {"x": x_data, "y": y_data}


@mcp.tool
def create_graph(title="", data=[]):
    """
    An invoke request is made to gpt-40-mini.
    The call takes two parameters title (the title of the graph) and data (the data points for the graph).
    """
    STYLE_NOTES = """
    Styling conventions to match:
    - Colors: PALETTE = ["#4C6EF5", "#F76707", "#12B886", "#FAB005", "#E64980", "#7048E8"]
    - Font: Helvetica Neue/Arial, size 14, color #2B2B2B; title size 22, left-aligned
    - Line charts: spline curves, width 3, markers size 9 with white outline
    - Bar charts: colored by category, labels outside bars, no border, bargap 0.35
    - Pie charts: donut style (hole=0.45), labels outside, slight slice separation
    """

    instruction = f"""
    You are a senior developer and expert statistician. You will be given data and a chart title.

    Three helper functions already exist in the target environment: line_chart(data, x_col, y_col, title, x_label, y_label), bar_chart(data, x_col, y_col, title, x_label, y_label), and pie_chart(data, names_col, values_col, title). Do NOT redefine these functions or restate their bodies — they already apply the styling described below internally.

    {STYLE_NOTES}

    Your job is only to:
    1. Build a `data` dict from the values provided.
    2. Transform data types if necessary or if suitable.
    3. Call the correct chart function with appropriate x_col/y_col (or names_col/values_col), title, and axis labels inferred from the data.
    4. Write a full python code with all the necessary imports, function, comments, and styling. 
    5. Call .show() on the result.

    Output ONLY the Python code for steps 1-5, in a single code block.
    """

    prompt = f"Write a Python code for a graph titled {title}, using these data: {data}"

    response = client.responses.create(
        model=MODEL,
        instructions=instruction,
        input=[{'role': 'user', 'content': prompt}],
        max_output_tokens=3000,
        temperature=1
    )

    code = response.output[0].content[0].text
    return code


if __name__ == "__main__":
    print("Starting MCP server on port 3008...", flush=True)
    try:
        mcp.run(transport="http", host="0.0.0.0", port=3008)
    except Exception as e:
        print("Server failed to start:", e, flush=True)
        raise