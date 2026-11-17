import requests

url = "https://api.openalex.org/works"

params = {
    "search": "retrieval augmented generation",
    "filter": "publication_year:2023-2025",
    "per_page": 5
}

response = requests.get(url, params=params, timeout=20)
response.raise_for_status()

for paper in response.json()["results"]:
    print(paper["title"], paper["publication_year"])