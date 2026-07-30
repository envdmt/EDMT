edmt.base
=========

.. py:module:: edmt.base


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/edmt/base/base/index






Package Contents
----------------

.. py:class:: AirdataBaseClass(api_key: str, skip_auth: bool = False)

   .. py:attribute:: api_key


   .. py:attribute:: base_url
      :value: 'api.airdata.com'



   .. py:attribute:: authenticated
      :value: False



   .. py:attribute:: auth_header


   .. py:method:: authenticate(validate=True)

      Authenticates with the API by calling /version or /flights.



.. py:function:: ExtractCSV(row: Union[dict, pandas.Series], col: str, max_retries: int = 3, timeout: int = 15) -> Optional[pandas.DataFrame]

   Fetches a CSV file from a URL specified in a given column of a metadata record.

   This function retrieves a CSV file from the URL found in the specified column (`col`)
   of the input `row`, parses it into a pandas DataFrame, and returns the result.
   It includes retry logic with exponential backoff to handle transient network errors.

   :param row: A metadata record containing a URL string in the
               column specified by `col`.
   :type row: dict or pandas.Series
   :param col: The key or column name in `row` that contains the URL to the CSV file.
   :type col: str
   :param max_retries: Maximum number of retry attempts in case of failure.
                       Defaults to 3.
   :type max_retries: int, optional
   :param timeout: Timeout for each HTTP request in seconds.
                   Defaults to 15 seconds.
   :type timeout: int or float, optional

   :returns:     - A pandas DataFrame containing the parsed CSV data if successful.
                 - `None` if the URL is missing, invalid, or if all retry attempts fail.
   :rtype: pandas.DataFrame or None

   :raises None:


