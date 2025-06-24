from edmt.contrib.utils import (
    clean_vars,
    normalize_column,
    dataframe_to_dict,
    clean_time_cols,
    format_iso_time
)


import base64
import http.client
import json
import requests
import pandas as pd


class Airdata:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "api.airdata.com"
        self.authenticated = False
        self.auth_header = self._get_auth_header()

        # Automatically authenticate on instantiation
        self.authenticate(validate=True)

    def _get_auth_header(self):
        """
        Manually constructs the Basic Auth header.
        Returns a properly encoded Authorization header dict.
        """
        key_with_colon = self.api_key + ":"
        encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_key}"
        }

    def authenticate(self, validate=True):
        """
        Authenticates with the Airdata API by calling /version or /flights.
        Sets self.authenticated = True if successful.
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

            # If /version not found, try /flights as fallback
            if res.status == 404:
                print("/version endpoint not found. Trying /flights...")
                conn = http.client.HTTPSConnection(self.base_url)
                conn.request("GET", "/flights", payload, self.auth_header)
                res = conn.getresponse()

            if res.status == 200:
                self.authenticated = True
                print("Authentication successful using /flights.")
            else:
                print(f"Authentication failed. Status code: {res.status}")
                print(f"Response: {res.read().decode('utf-8')[:200]}")
                if validate:
                    raise ValueError("Authentication failed: Invalid API key or permissions.")

        except Exception as e:
            print(f"⚠️ Network error during authentication: {e}")
            if validate:
                raise

    def get_flights(
        self,
        since: str | None = None,
        until: str | None = None,
        detail_level: bool = False,
        limit: int | None = None,
        created_after: str | None = None,
        battery_ids: list | None = None,
        pilot_ids: list | None = None,
        location: list | None = None,  # Should be [lat, lon]
    ) -> pd.DataFrame:
        """
        Fetch flight data from the Airdata API based on the provided query parameters.

        Parameters:
            since (str or None): 
                Filter flights that started after this date/time (ISO 8601 format). 
                Example: '2025-01-01T00:00:00'.
            until (str or None): 
                Filter flights that started before this date/time (ISO 8601 format).
                Example: '2025-03-31T23:59:59'.
            detail_level (bool): 
                If True, returns comprehensive flight details. If False, returns basic information.
                Maps to 'detail_level=comprehensive' or 'basic' in API request.
            limit (int or None): 
                Maximum number of results to return. Default is None (no limit specified).
            created_after (str or None): 
                Filter flights created after the given date/time (ISO 8601 format).
            battery_ids (list or None): 
                List of battery IDs to filter flights by associated battery.
            pilot_ids (list or None): 
                List of pilot IDs to filter flights by pilot.
            location (list or None): 
                Optional geographic coordinates as a two-item list `[latitude, longitude]` 
                to filter flights near that location.

        Returns:
            pd.DataFrame: A DataFrame containing the retrieved flight data. 
                        If the request fails or no data is found, returns an empty DataFrame.

        Raises:
            ValueError: 
                If `location` is not a list of exactly two numeric values (latitude and longitude).

        Example:
            >>> client.get_flights(
            ...     since='2025-01-01T00:00:00',
            ...     until='2025-03-31T23:59:59',
            ...     detail_level=True,
            ...     limit=5,
            ...     location=[37.7749, -122.4194]
            ... )
            # Returns a DataFrame with up to 5 comprehensive flights near San Francisco
        """

        # Validate location format: must be None or a list with exactly 2 numeric items
        if location is not None:
            if not isinstance(location, list) or len(location) != 2 or not all(isinstance(x, (int, float)) for x in location):
                raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

        since = format_iso_time(since).replace("T", "+") if since else None
        until = format_iso_time(until).replace("T", "+") if until else None
        created_after = format_iso_time(created_after).replace("T", "+") if created_after else None
        detail_level_str = "comprehensive" if detail_level else "basic"

        params = {
            "start": since,
            "end": until,
            "detail_level": detail_level_str,
            "created_after": created_after,
            "battery_ids": ",".join(battery_ids) if battery_ids else None,
            "pilot_ids": ",".join(pilot_ids) if pilot_ids else None,
            "latitude": location[0] if location else None,
            "longitude": location[1] if location else None,
            "limit": limit
        }

        # Remove None values from params
        params = {k: v for k, v in params.items() if v is not None}

        url = "/flights?" + "&".join([f"{k}={v}" for k, v in params.items()]) # Construct URL with query string
        
        # Make sure user is authenticated
        if not self.authenticated:
            print("Cannot fetch flights: Not authenticated.")
            return None
        
        conn = http.client.HTTPSConnection(self.base_url)
        conn.request("GET", url, headers=self.auth_header)
        res = conn.getresponse()

        if res.status == 200:
            data = json.loads(res.read().decode("utf-8"))
            df = pd.DataFrame(data)
            print(df)
        
        # Send request
        try:
            conn = http.client.HTTPSConnection(self.base_url)
            conn.request("GET", url, headers=self.auth_header)
            res = conn.getresponse()

            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                df = pd.DataFrame(data)
                df = pd.json_normalize(df['data'])
                return df
            else:
                print(f"Failed to fetch flights. Status code: {res.status}")
                print(f"Response: {res.read().decode('utf-8')[:500]}")
                return None
        except Exception as e:
            print(f"Error fetching flights: {e}")
            return None








