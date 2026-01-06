import logging
logger = logging.getLogger(__name__)
import base64
import http.client
import requests
import pandas as pd
import requests
from io import StringIO
import time

logging.basicConfig(level=logging.WARNING)

# API key authentication
class AirdataBaseClass:
        def __init__(self, api_key):
            self.api_key = api_key
            self.base_url = "api.airdata.com"
            self.authenticated = False
            self.auth_header = self._get_auth_header()

            self.authenticate(validate=True)

        def _get_auth_header(self):
            key_with_colon = self.api_key + ":"
            encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
            return {
                "Authorization": f"Basic {encoded_key}"
            }

        def authenticate(self,validate=True):
            """
            Authenticates with the API by calling /version or /flights.
            """
            conn = http.client.HTTPSConnection(self.base_url)
            payload = ''

            try:
                conn.request("GET", "/version", payload, self.auth_header)
                res = conn.getresponse()
                
                if res.status == 200:
                    self.authenticated = True
                    print("Authentication successful.")
                    return

                if res.status == 404:
                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", "/flights", payload, self.auth_header)
                    res = conn.getresponse()

                if res.status == 200:
                    self.authenticated = True
                    print("Authentication successful.")
                else:
                    print(f"Authentication failed. Status code: {res.status}")
                    print(f"Response: {res.read().decode('utf-8')[:200]}")
                    if validate:
                        raise ValueError("Authentication failed: Invalid API key or permissions.")

            except Exception as e:
                print(f"Network error during authentication: {e}")
                if validate:
                    raise


def AirdataCSV(
        row, 
        col : str,
        max_retries : int = 3, 
        timeout : int = 15
        ) -> pd.DataFrame:
    """
    Fetches a CSV file from a URL specified in a given column of a metadata record.

    This function retrieves a CSV file from the URL found in the specified column (`col`)
    of the input `row`, parses it into a pandas DataFrame, and returns the result.
    It includes retry logic with exponential backoff to handle transient network errors.

    Args:
        row (dict or pandas.Series): A metadata record containing a URL string in the 
            column specified by `col`.
        col (str): The key or column name in `row` that contains the URL to the CSV file.
        max_retries (int, optional): Maximum number of retry attempts in case of failure.
            Defaults to 3.
        timeout (int or float, optional): Timeout for each HTTP request in seconds.
            Defaults to 15 seconds.

    Returns:
        pandas.DataFrame or None:
            - A pandas DataFrame containing the parsed CSV data if successful.
            - `None` if the URL is missing, invalid, or if all retry attempts fail.

    Raises:
        None
    """
    csv_link = row[col]
    if not isinstance(csv_link, str) or not csv_link.strip():
        return None

    for attempt in range(max_retries):
        try:
            resp = requests.get(csv_link.strip(), timeout=timeout)
            resp.raise_for_status()

            csv_df = pd.read_csv(StringIO(resp.text), low_memory=False)
            return csv_df
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(0.5 * (2 ** attempt))

