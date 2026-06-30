import requests_async
import os
from pydantic import BaseModel
import json
import logging

logger = logging.getLogger("goober")

class CredCache(BaseModel):
    access_token: str
    expires_at: int

class StravaApi:
    def __init__(self) -> None:
        try:
            self.client_secret = os.environ["STRAVA_CLIENT_SECRET"]
            self.refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]
            self.client_id = os.environ["STRAVA_CLIENT_ID"]
        except KeyError as _:
            logger.error("Strava keys not defined")

        self.cred_cache: CredCache | None = None

    async def refresh_access_token(self) -> CredCache:
        url = f"https://www.strava.com/api/v3/oauth/token?client_id={self.client_id}&client_secret={self.client_secret}&grant_type=refresh_token&refresh_token={self.refresh_token}"

        res = await requests_async.post(url, headers={
            "Content-Type": "application/json"
        })

        if res.status_code != 200:
            raise ValueError(f"Invalid response! {res.text}")
        
        jason = res.json()
        self.cred_cache = CredCache(access_token=jason["access_token"], expires_at=jason["expires_at"])

        return self.cred_cache
    
    async def get_activities(self) -> None:
        if not self.cred_cache:
            self.cred_cache = await self.refresh_access_token()

        res = await requests_async.get("https://www.strava.com/api/v3/athlete/activities?per_page=10", headers={
            "Authorization": f"Bearer {self.cred_cache.access_token}"
        })

        logger.info(json.dumps(res.json(), indent=2))

instance = StravaApi()