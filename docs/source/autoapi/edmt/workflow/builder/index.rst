edmt.workflow.builder
=====================

.. py:module:: edmt.workflow.builder






Module Contents
---------------

.. py:function:: ee_initialized(project: str | None = None) -> None

   Initialize Earth Engine only once.

   Notes:
   - Uses the public ee.data.is_initialized() instead of private ee.data._initialized.
   - Newer EE setups typically require a Cloud project for Initialize().


.. py:function:: gdf_to_ee_geometry(gdf: geopandas.GeoDataFrame) -> ee.Geometry

.. py:function:: _norm(x: Optional[str]) -> str

.. py:function:: _copy_time(img: ee.Image) -> ee.Image

.. py:function:: _ndvi_from_nir_red(nir: ee.Image, red: ee.Image) -> ee.Image

.. py:function:: _evi_from_nir_red_blue(nir: ee.Image, red: ee.Image, blue: ee.Image) -> ee.Image

.. py:data:: Frequency

.. py:function:: _advance_end(start: ee.Date, frequency: str) -> ee.Date

.. py:function:: _dates_for_frequency(start_date: str, end_date: str, frequency: str) -> ee.List

.. py:function:: _timeseries_to_df(fc: ee.FeatureCollection) -> pandas.DataFrame

.. py:function:: _build_lst(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]

.. py:function:: _build_ndvi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]

.. py:function:: _build_evi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]

.. py:function:: _build_ndvi_evi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]

.. py:function:: _build_chirps(start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]

.. py:function:: _empty(prod: str, start: ee.Date) -> ee.Feature

.. py:function:: _compute(prod: str, start: ee.Date, period_ic: ee.ImageCollection, geometry: ee.Geometry, scale: int, meta: Dict[str, Any]) -> ee.Feature

.. py:data:: ReducerName

.. py:function:: _compute_img(product: str, start_date: str, end_date: str, ic: ee.ImageCollection, meta: Dict[str, Any], roi: Optional[ee.Geometry] = None, reducer: ReducerName = 'mean') -> ee.Image

   Build a single composite ee.Image for a product using (ic, meta) from get_satellite_collection().

   - CHIRPS: reducer='sum' => total mm over period; else statistic of daily mm/day
   - NDVI/EVI: statistic over index band
   - NDVI_EVI: statistic over both bands (NDVI & EVI)
   - LST: statistic over band then convert to °C using meta (DN->K->C or K->C)


.. py:function:: _period_dates(start_date: str, end_date: str, frequency: str) -> Tuple[str, int]

.. py:function:: _empty_img(start: ee.Date, end: ee.Date, freq: str, prod: str) -> ee.Image

.. py:function:: _build_period_img(prod: str, r: str, start: ee.Date, end: ee.Date, period_ic: ee.ImageCollection, meta: Dict[str, Any], roi: Optional[ee.Geometry]) -> ee.Image

   Build one composite image for the period (server-side safe).


