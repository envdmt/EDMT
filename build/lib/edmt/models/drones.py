import requests
from requests.auth import HTTPBasicAuth
import pandas as pd

from edmt.contrib.utils import (
    clean_vars,
    normalize_column,
    dataframe_to_dict,
    clean_time_cols,
    format_iso_time
)

class Airdata:
    def __init__(
            self, 
            api_key: str | None = None, 
            **kwargs):
        self.api_key = api_key
        self.base_url = "https://api.airdata.com" 

        for key, value in kwargs.items():
            setattr(self, key, value)

    def authentication(self):
        """
        Authenticates and validates the API key by calling /version endpoint.
        Returns (auth_object, is_valid) tuple.
        """
        url = f"{self.base_url}/version"
        auth = HTTPBasicAuth(self.api_key, "")

        try:
            response = requests.get(url, auth=auth, params={"limit": 1})
            is_valid = response.status_code == 200
            if not is_valid:
                print(f"❌ Authentication failed. Status code: {response.status_code}")
            return auth, is_valid
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error during authentication: {e}")
            return auth, False

    def account_keys(self):
        """
        Fetches account API keys from the server.
        Returns DataFrame if successful, empty DataFrame otherwise.
        """
        url = f"{self.base_url}/accounts/keys"
        auth = HTTPBasicAuth(self.api_key, "")

        try:
            response = requests.get(url, auth=auth)
            if response.status_code == 200:
                df = pd.DataFrame(response.json())
                return df
            else:
                print(f"❌ Error fetching account keys. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error while fetching account keys: {e}")
            return pd.DataFrame()

    def get_flights(
            self, 
            since: str | None = None, 
            until: str | None = None,
            detail_level=False,):
        """
        Fetch flight data based on provided query parameters.

        Parameters:
            since : str | datetime-like
                Show flights that started after this date (ISO formatted).
            until : str | datetime-like
                Show flights that started before this date (ISO formatted).
            detail_level : bool
                If True -> 'comprehensive', if False -> 'basic'
        
        Returns:
            pd.DataFrame: Flight data if successful, empty DataFrame otherwise.
        """
        # Format time inputs
        since = format_iso_time(since)
        until = format_iso_time(until)

        # Set detail level
        detail_level_str = "comprehensive" if detail_level else "basic"

        url = f"{self.base_url}/flights"
        params = {
            "start": since,
            "end": until,
            "detail_level": detail_level_str,
        }

        auth, is_valid = self.authentication()
        if not is_valid:
            print("❌ Aborting request: Invalid authentication.")
            return pd.DataFrame()

        try:
            response = requests.get(url, auth=auth, params=params)
            if response.status_code == 200:
                df = pd.DataFrame(response.json())
                df = normalize_column(df, "data")
                return df
            else:
                print(f"❌ Failed to fetch flights. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error while fetching flights: {e}")
            return pd.DataFrame()

# class Airdata:
#     def __init__(self, api_key: str,**kwargs):
#         self.api_key = api_key
#         self.base_url = 'https://api.airdata.com'

#         for key, value in kwargs.items():
#             setattr(self, key, value)

#     def authentication(self):
#         """
#         Authenticates and validates the API key.
#         Fetches /version endpoint to verify connectivity/authentication.
#         Returns version info if successful, None otherwise.
#         """
#         url = f"{self.base_url}/version"
#         auth = HTTPBasicAuth(self.api_key, '')

#         try:
#             response = requests.get(url, auth=auth, params={'limit': 1})
#             is_valid = response.status_code == 200
#             if not is_valid:
#                 print(f"❌ Authentication failed. Status code: {response.status_code}")
#             return auth, is_valid
#         except requests.exceptions.RequestException as e:
#             print(f"⚠️ Network error during authentication: {e}")
#             return auth, False
    
#     # Get Account API keys
#     def account_keys(self):
#         url = f"{self.base_url}/accounts/keys"
#         auth = auth = HTTPBasicAuth(self.api_key, '')

#         response = requests.get(url,auth)
#         if response.status_code == 200:
#             df = pd.DataFrame(response.json())
#             return df
#         else:
#             print(f"Error {response.status_code}: {response.text}")
#             return pd.DataFrame()


#     def get_flights(
#             self, 
#             since: str | None = None, 
#             until: str | None = None,
#             detail_level=False,):
#         """
#         Fetch flight data based on provided query parameters.
        
#         Parameters:
#             since : Formatted date - show flights that started after this date. Flight time is searched by local flight time.
#                 Example: since=2019-05-01+00:00:00
#             until : show flights that started before this date.
#                 Example: until=2019-05-01+00:00:00
#             detail_level : The amount of information to include in the response:
#                         basic for basic information, which takes False
#                         comprehensive for extended information, takes True
#                         Example: detail_level=True, for comprehensive

            
#         """
#         since = format_iso_time(since)
#         until = format_iso_time(until)

#         if detail_level==True:
#             detail_level = "comprehensive"
#         else:
#             detail_level = "basic"

#         params = {
#             "start" : since,
#             "end" : until,
#             "detail_level" : detail_level
#         }

#         auth = self.authentication()
#         response = requests.get(self.base_url + "flights", auth=auth, params=params)

#         if response.status_code == 200:
#             data = pd.DataFrame(response.json())
#             df = normalize_column(data, "data")
#             return df
#         else:
#             print(f"Error {response.status_code}: {response.text}")
#             return pd.DataFrame()
        

    # def get_subjectsources(
    #     self, subjects: str | None = None, sources: str | None = None, **addl_kwargs
    # ) -> pd.DataFrame:
    #     """
    #     Parameters
    #     ----------
    #     subjects: A comma-delimited list of Subject IDs.
    #     sources: A comma-delimited list of Source IDs.
    #     Returns
    #     -------
    #     subjectsources : pd.DataFrame
    #     """
    #     params = clean_kwargs(addl_kwargs, sources=sources, subjects=subjects)
    #     df = pd.DataFrame(
    #         self.get_objects_multithreaded(
    #             object="subjectsources/",
    #             threads=self.tcp_limit,
    #             page_size=self.sub_page_size,
    #             **params,
    #         )
    #     )
    #     df = clean_time_cols(df)
    #     return df


