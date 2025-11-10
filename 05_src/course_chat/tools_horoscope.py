from langchain.tools import tool
import requests
import json
from utils.logger import get_logger

_logs = get_logger(__name__)

@tool
def get_horoscope(sign:str, date:str = "TODAY") -> str:
    """
    An API call to a horoscope service is made.
    The API call is to https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily
    and takes two parameters sign and date.
    Accepted values for sign are: Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpio, Sagittarius, Capricorn, Aquarius, Pisces
    Accepted values for date are: Date in format (YYYY-MM-DD) OR "TODAY" OR "TOMORROW" OR "YESTERDAY".
    """
    _logs.debug(f'Getting horoscope for sign {sign}, and date {date}')
    response = get_horoscope_from_service(sign, date)
    horoscope = get_horoscope_from_response(sign, response)
    _logs.debug(f'Horoscope result: {horoscope}')
    return horoscope



def get_horoscope_from_service(sign:str, day:str):
    url = "https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily"
    params = {
        "sign": sign.capitalize(),
        "day": day.upper()
    }
    response = requests.get(url, params=params)
    return response



def get_horoscope_from_response(sign:str, response:requests.Response) -> str:
    resp_dict = json.loads(response.text)
    data = resp_dict.get("data")
    horoscope_data = data.get("horoscope_data", "No horoscope found.")
    date = data.get("date", "No date found.")
    horoscope = f"Horoscope for {sign.capitalize()} on {date}: {horoscope_data}"
    return horoscope