import requests
import time
import boto3
import json
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()


# Replace with your Riot API key
RIOT_API_KEY = os.environ.get("RIOT_API_KEY")
HEADERS = {"X-Riot-Token": RIOT_API_KEY}


def get_puuid(game_name, tag_line, region="na1"):
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("puuid")
    else:
        print(f"Error fetching PUUID: {response.status_code} - {response.text}")
        return None


def get_match_ids(puuid, region="americas", count=20):
    url = f"https://{region}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}/?start=0&count={count}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("matches")
    else:
        print(f"Error fetching match IDs: {response.status_code} - {response.text}")
        return []


def get_match_details(match_id, region="americas"):
    url = f"https://{region}.api.riotgames.com/val/match/v1/matches/{match_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching match details: {response.status_code} - {response.text}")
        return None


def upload_to_s3(file_name, data):
    s3 = boto3.client("s3")
    bucket_name = "valorant-player-data"
    s3.put_object(Bucket=bucket_name, Key=file_name, Body=json.dumps(data))
    print(f"Uploaded {file_name} to S3")
