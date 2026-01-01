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


def AirdataCSV(row, retries=3, timeout=10):
    """
    Fetches and processes a CSV file from a URL specified in a metadata row.

    This function downloads a CSV file from the URL provided in the 'csvLink' field of
    the input `row`, parses it into a pandas DataFrame, and merges it with the metadata
    from `row` (repeated for each row of the CSV). It includes robust retry logic
    with exponential backoff to handle transient network issues.

    Args:
        row (dict or pandas.Series): A metadata record containing at least the key
            'csvLink' with a valid URL string pointing to a CSV file.
        retries (int, optional): Maximum number of retry attempts in case of failure.
            Defaults to 3.
        timeout (int or float, optional): Request timeout in seconds for each HTTP attempt.
            Defaults to 10 seconds.

    Returns:
        pandas.DataFrame or None: 
            - A DataFrame combining the downloaded CSV data with the input metadata 
              (each CSV row is annotated with the full metadata from `row`).
            - Returns `None` if the URL is missing/invalid or if all retry attempts fail.
    Raises:
        None
    """
    csv_link = row.get('csvLink')
    if not isinstance(csv_link, str) or not csv_link.strip():
        return None

    for attempt in range(retries):
        try:
            resp = requests.get(csv_link.strip(), timeout=timeout)
            resp.raise_for_status()
            csv_data = pd.read_csv(StringIO(resp.text), low_memory=False)
            metadata_repeated = pd.DataFrame([row] * len(csv_data), index=csv_data.index)
            combined = pd.concat([metadata_repeated, csv_data], axis=1)
            return combined
        except Exception as e:
            if attempt == retries - 1:
                # logging.warning(f"Failed to fetch {csv_link} after {retries} attempts: {e}")
                return None
            time.sleep(0.5 * (2 ** attempt))

