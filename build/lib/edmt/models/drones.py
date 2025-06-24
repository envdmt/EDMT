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
    def __init__(self, api_key,**kwargs):
        self.api_key = api_key
        self.base_url = 'https://api.airdata.com'

        for key, value in kwargs.items():
            setattr(self, key, value)

    def authentication(self):
        """
        Authenticates and validates the API key.
        Fetches /version endpoint to verify connectivity/authentication.
        Returns version info if successful, None otherwise.
        """
        url = f"{self.base_url}/version"
        auth = HTTPBasicAuth(self.api_key, '')

        try:
            response = requests.get(url, auth=auth, params={'limit': 1})
            is_valid = response.status_code == 200
            if not is_valid:
                print(f"❌ Authentication failed. Status code: {response.status_code}")
            return auth, is_valid
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error during authentication: {e}")
            return auth, False
    
    # Get Account API keys
    def account_keys(self):
        url = f"{self.base_url}/accounts/keys"
        auth = auth = HTTPBasicAuth(self.api_key, '')

        response = requests.get(url,auth)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            return df
        else:
            print(f"Error {response.status_code}: {response.text}")
            return pd.DataFrame()




    def get_flights(self, since=None, until=None,detail_level=False,):
        """
        Fetch flight data based on provided query parameters.
        
        Parameters:
            since : Formatted date - show flights that started after this date. Flight time is searched by local flight time.
                Example: since=2019-05-01+00:00:00
            until : show flights that started before this date.
                Example: until=2019-05-01+00:00:00
            detail_level : The amount of information to include in the response:
                        basic for basic information, which takes False
                        comprehensive for extended information, takes True
                        Example: detail_level=True, for comprehensive

            
        """
        since = format_iso_time(since)
        until = format_iso_time(until)

        if detail_level==True:
            detail_level = "comprehensive"
        else:
            detail_level = "basic"

        params = {
            "start" : since,
            "end" : until,
            "detail_level" : detail_level
        }

        auth = self.authentication()
        response = requests.get(self.base_url + "flights", auth=auth, params=params)

        if response.status_code == 200:
            data = response.json()
            data = pd.DataFrame(data)
            df = normalize_column(data, "data")
            return df
        else:
            print(f"Error {response.status_code}: {response.text}")
            return pd.DataFrame()
        

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