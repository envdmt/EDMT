edmt.contrib
============

.. py:module:: edmt.contrib


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/edmt/contrib/utils/index




Package Contents
----------------

.. py:function:: clean_vars(addl_kwargs={}, **kwargs)

.. py:function:: norm_exp(df: pandas.DataFrame, cols: Union[str, list]) -> pandas.DataFrame

   Normalizes specified columns containing list of dicts,
   expands them into separate rows if needed,
   and appends new columns to the original dataframe with prefixing.

   Parameters:
   - df: Original pandas DataFrame
   - cols: str or list of str, names of columns to normalize

   Returns:
   - Modified DataFrame with normalized and expanded data


.. py:function:: normalize_column(df, col)

.. py:function:: format_iso_time(date_string: str) -> str

.. py:function:: append_cols(df: pandas.DataFrame, cols: Union[str, list])

   Move specified column(s) to the end of the DataFrame.

   :param df: Input DataFrame.
   :type df: pd.DataFrame
   :param cols: Column name(s) to move to the end.
   :type cols: str or list

   :returns: DataFrame with columns reordered.
   :rtype: pd.DataFrame


.. py:function:: dict_expand(data, cols)

