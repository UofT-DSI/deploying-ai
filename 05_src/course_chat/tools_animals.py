from langchain.tools import tool
import json
import requests


@tool
def get_cat_facts(n:int=1):
    """
    Returns n cat facts from the Meowfacts API.
    """
    url = "https://meowfacts.herokuapp.com/"
    params = {
        "count": n
    }
    response = requests.get(url, params=params)
    resp_dict = json.loads(response.text)
    facts_list = resp_dict.get("data", [])
    facts = "\n".join([f"{i+1}. {fact}\n" for i, fact in enumerate(facts_list)])
    return facts

@tool
def get_dog_facts(n:int=1):
    """
    Returns n dog facts from the Dog API.
    """
    url = "http://dogapi.dog/api/v2/facts"
    params = {
        "limit": n
    }
    response = requests.get(url, params=params)
    resp_dict = json.loads(response.text)
    facts_list = resp_dict.get("data", [])
    facts = "\n".join([f"{i+1}. {fact['attributes']['body']}\n" for i, fact in enumerate(facts_list)])
    return facts
