from edmt.contrib.utils import (
    format_iso_time,
    append_cols,
    norm_exp
)
import logging
logger = logging.getLogger(__name__)

from typing import Union
import base64
import http.client
import json
import requests

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point

from io import StringIO
from tqdm import tqdm
from typing import Union, Optional

from pyproj import Geod
geod = Geod(ellps="WGS84")

# "https://api.airdata.com/flight_upload_auth?appkey=abcd1234&usertoken=HD1234abcd"

class AirdataUploadAuth:
    def __init__(self, api_key, user_token: str):
        self.api_key = api_key
        self.user_token = user_token
        self.base_url = "api.airdata.com"
        self.authenticated = False
        self.auth_header = self._get_auth_header()
        self.authenticate(validate=True)

        if not self.api_key or not self.user_token:
            raise ValueError("API key and user token must be provided.")
        if not isinstance(self.api_key, str) or not isinstance(self.user_token, str):
            raise TypeError("API key and user token must be strings.")

    def _get_auth_header(self):
        key_with_colon = self.api_key + ":"
        encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_key}"
        }

    def authenticate(self,validate=True):
        """
        Authenticates with the API flight_upload_auth.
        """
        conn = http.client.HTTPSConnection(self.base_url)
        payload = ''
        try:
            conn.request("GET", "/flight_upload_auth", payload, self.auth_header)
            res = conn.getresponse()
            if res.status == 200:
                self.authenticated = True
                print("✅ Authentication successful.")
                return
            else:
                print(f"❌ Authentication failed. Status code: {res.status}")
                if validate:
                    raise ValueError("Authentication failed: Invalid API key or permissions.")
        except Exception as e:
            print(f"⚠️ Network error during authentication: {e}")
            if validate:
                raise
    
    def upload_flight(self, file_path: str, app_name: str, app_version: str) -> Optional[dict]:
        """
        Uploads a flight file to the Airdata API.

        Parameters:
            file_path (str): Path to the flight file to be uploaded.
            app_name (str): Name of the application uploading the flight.
            app_version (str): Version of the application.

        Returns:
            Optional[dict]: A dictionary containing the response from the upload request.
                            Returns None if the upload fails or is not authenticated.
        """
        if not self.authenticated:
            print("Cannot upload flight: Not authenticated.")
            return None

        try:
            with open(file_path, 'rb') as file:
                conn = http.client.HTTPSConnection(self.base_url)
                headers = {
                    "Authorization": f"Basic {self._get_auth_header()['Authorization']}",
                    "Content-Type": "multipart/form-data"
                }
                params = {
                    "appkey": self.api_key,
                    "usertoken": self.user_token,
                    "appname": app_name,
                    "appversion": app_version,
                    "file": file
                }
                conn.request("POST", "/flight_upload", body=params, headers=headers)
                res = conn.getresponse()

                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    return data
                else:
                    print(f"Failed to upload flight. Status code: {res.status}")
                    print(f"Response: {res.read().decode('utf-8')[:500]}")
                    return None
        except Exception as e:
            print(f"Error uploading flight: {e}")
            return None
        


    def get_flights(
              self,since: str = None,until: str = None,limit: Union[int, None] = None,
              created_after: Optional[str] = None,battery_ids: Optional[Union[str, list]] = None,
              pilot_ids: Optional[Union[str, list]] = None,location: Optional[list] = None,
          ) -> pd.DataFrame:

          """
          Fetch flight data from the Airdata API based on the provided query parameters.

          Returns:
              pd.DataFrame: A DataFrame containing the retrieved flight data.
                          If the request fails or no data is found, returns an empty DataFrame.

          Raises:
              ValueError:
                  If `location` is not a list of exactly two numeric values (latitude and longitude).
          """

          if location is not None:
              if not isinstance(location, list) or len(location) != 2 or not all(isinstance(x, (int, float)) for x in location):
                  raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

          formatted_since = format_iso_time(since).replace("T", "+") if since else None
          formatted_until = format_iso_time(until).replace("T", "+") if until else None
          formatted_created_after = format_iso_time(created_after).replace("T", "+") if created_after else None

          params = {
              "start": formatted_since,
              "end": formatted_until,
              "detail_level": "comprehensive",
              "created_after": formatted_created_after,
              "battery_ids": ",".join(battery_ids) if battery_ids else None,
              "pilot_ids": ",".join(pilot_ids) if pilot_ids else None,
              "latitude": location[0] if location else None,
              "longitude": location[1] if location else None,
              "limit": limit
          }

          params = {k: v for k, v in params.items() if v is not None}

          endpoint = "/flights?" + "&".join([f"{k}={v}" for k, v in params.items()])
          
          if not self.authenticated:
              print("Cannot fetch flights: Not authenticated.")
              return None
                  
          try:
              conn = http.client.HTTPSConnection(self.base_url)
              conn.request("GET", endpoint, headers=self.auth_header)
              res = conn.getresponse()

              if res.status == 200:
                  data = json.loads(res.read().decode("utf-8"))
                  if "data" in data: 
                      normalized_data = list(tqdm(data["data"], desc="📥 Downloading"))
                      df = pd.json_normalize(normalized_data)
                      df = df.drop(
                          columns=[
                              "displayLink","kmlLink",
                              "gpxLink","originalLink",
                              "participants.object"
                          ],
                          errors='ignore'
                      )
                  else:
                    df = pd.DataFrame(data)
                  return df
              else:
                  print(f"Failed to fetch flights. Status code: {res.status}")
                  print(f"Response: {res.read().decode('utf-8')[:500]}")
                  return None
          except Exception as e:
              print(f"Error fetching flights: {e}")
              return None


# class AirdataUploadAuth:
#     def __init__(self, api_key: str, user_token: str):
#         self.api_key = api_key
#         self.user_token = user_token
#         self.base_url = "api.airdata.com"
#         self.authenticated = False
#         self.auth_header = self._get_auth_header()

#     def _get_auth_header(self):
#         key_with_colon = f"{self.api_key}:{self.user_token}"
#         encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
#         return {
#             "Authorization": f"Basic {encoded_key}"
#         }

#     def authenticate(self) -> bool:
#         """
#         Authenticates with the API by calling /flight_upload_auth.
#         """
#         conn = http.client.HTTPSConnection(self.base_url)
#         payload = ''
        
#         try:
#             conn.request("GET", "/flight_upload_auth", payload, self.auth_header)
#             res = conn.getresponse()
            
#             if res.status == 200:
#                 self.authenticated = True
#                 print("✅ Authentication successful.")
#                 return True

#             print(f"❌ Authentication failed. Status code: {res.status}")
#             print(f"Response: {res.read().decode('utf-8')[:200]}")
#             return False

#         except Exception as e:
#             print(f"⚠️ Network error during authentication: {e}")
#             return False
        

#     def get_upload_auth(self) -> Optional[dict]:
#         """
#         Fetches upload authentication details from the Airdata API.

#         Returns:
#             Optional[dict]: A dictionary containing the upload authentication details.
#                             Returns None if the request fails or is not authenticated.
#         """
#         if not self.authenticated:
#             print("Cannot fetch upload auth: Not authenticated.")
#             return None

#         try:
#             conn = http.client.HTTPSConnection(self.base_url)
#             conn.request("GET", "/flight_upload_auth", headers=self.auth_header)
#             res = conn.getresponse()

#             if res.status == 200:
#                 data = json.loads(res.read().decode("utf-8"))
#                 return data
#             else:
#                 print(f"Failed to fetch upload auth. Status code: {res.status}")
#                 print(f"Response: {res.read().decode('utf-8')[:500]}")
#                 return None
#         except Exception as e:
#             print(f"Error fetching upload auth: {e}")
#             return None

#     def upload_flight(self, file_path: str, app_name: str, app_version: str) -> Optional[dict]:
#         """
#         Uploads a flight file to the Airdata API.

#         Parameters:
#             file_path (str): Path to the flight file to be uploaded.
#             app_name (str): Name of the application uploading the flight.
#             app_version (str): Version of the application.

#         Returns:
#             Optional[dict]: A dictionary containing the response from the upload request.
#                             Returns None if the upload fails or is not authenticated.
#         """
#         if not self.authenticated:
#             print("Cannot upload flight: Not authenticated.")
#             return None

#         try:
#             with open(file_path, 'rb') as file:
#                 conn = http.client.HTTPSConnection(self.base_url)
#                 headers = {
#                     "Authorization": f"Basic {self._get_auth_header()['Authorization']}",
#                     "Content-Type": "multipart/form-data"
#                 }
#                 params = {
#                     "appkey": self.api_key,
#                     "usertoken": self.user_token,
#                     "appname": app_name,
#                     "appversion": app_version,
#                     "file": file
#                 }
#                 conn.request("POST", "/flight_upload", body=params, headers=headers)
#                 res = conn.getresponse()

#                 if res.status == 200:
#                     data = json.loads(res.read().decode("utf-8"))
#                     return data
#                 else:
#                     print(f"Failed to upload flight. Status code: {res.status}")
#                     print(f"Response: {res.read().decode('utf-8')[:500]}")
#                     return None
#         except Exception as e:
#             print(f"Error uploading flight: {e}")
#             return None
        

