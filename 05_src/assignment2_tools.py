import csv
def fetch_music_db():
    """Fetches the music database from a remote source.

    This function simulates fetching a music database by returning
    a predefined list of dictionaries, each representing a music track.

    Returns:
        list: A list of dictionaries, each containing details about a music track.
    """
    music_db = [
        {"title": "Song A", "artist": "Artist 1", "album": "Album X", "year": 2020},
        {"title": "Song B", "artist": "Artist 2", "album": "Album Y", "year": 2019},
        {"title": "Song C", "artist": "Artist 1", "album": "Album Z", "year": 2021},
        {"title": "Song D", "artist": "Artist 3", "album": "Album X", "year": 2018},
    ]
    return music_db


@Tools
def fetch_on_air_movie(max_results=100):
    movies = []
    try:
        csv_path = "on_air_movies.csv"
        with open(csv_path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for row in range(max_results):
                # normalize keys and types
                movie = {k.strip(): v.strip() for k, v in row.items() if v is not None}
                # convert year to int when possible
                movies.append(movie)
    except FileNotFoundError:
        # If CSV is missing, return an empty list (caller can handle)
        return []
    return movies