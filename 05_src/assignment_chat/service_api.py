import requests

def get_quote():
    url = "https://zenquotes.io/api/random"
    response = requests.get(url).json()

    quote = response[0]['q']
    author = response[0]['a']

    # Transform response (required by assignment)
    return quote,author

