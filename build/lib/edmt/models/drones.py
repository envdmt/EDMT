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

