edmt.workflow.builder
=====================

.. py:module:: edmt.workflow.builder






Module Contents
---------------

.. py:data:: Frequency

.. py:data:: ReducerName

.. py:function:: ee_initialized(project: str | None = None) -> None

   Initialize Earth Engine only once.

   Notes:
   - Uses the public ee.data.is_initialized() instead of private ee.data._initialized.
   - Newer EE setups typically require a Cloud project for Initialize().


.. py:function:: gdf_to_ee_geometry(gdf: geopandas.GeoDataFrame) -> ee.Geometry

.. py:function:: _norm_sat(x: Optional[str]) -> str

.. py:function:: _freq_unit(frequency: str) -> str

.. py:function:: _advance_end(start: ee.Date, frequency: str) -> ee.Date

.. py:function:: _make_dates(start: ee.Date, end: ee.Date, frequency: str) -> ee.List

.. py:function:: _timeseries_to_df(fc: ee.FeatureCollection) -> pandas.DataFrame

.. py:function:: _empty(prod: str, start: ee.Date, meta: Dict[str, Any] = None) -> ee.Feature

.. py:data:: _PRODUCT_REGISTRY

.. py:data:: _SAT_CONFIG

.. py:function:: _ndvi_from_nir_red(nir: ee.Image, red: ee.Image) -> ee.Image

.. py:function:: _evi_from_nir_red_blue(nir: ee.Image, red: ee.Image, blue: ee.Image) -> ee.Image

.. py:function:: _mask_s2(img)

.. py:function:: _mask_landsat(img)

.. py:function:: _sr(img, band)

.. py:function:: _scale_lst(img, band, scale_cfg)

.. py:function:: _build_lst(satellite, start_date, end_date)

.. py:function:: _build_vegetation(product, satellite, start_date, end_date)

.. py:function:: _build_chirps(start_date, end_date)

.. py:function:: _compute_lst(start, period_ic, geometry, scale, meta, n=None)

.. py:function:: _compute_veg(prod, start, period_ic, geometry, scale, meta)

.. py:function:: _compute_chirps(start, period_ic, geometry, scale, meta)

.. py:data:: _COMPUTE_REGISTRY

.. py:function:: _compute(prod: str, start: ee.Date, period_ic: ee.ImageCollection, geometry: ee.Geometry, scale: int, meta: Dict[str, Any]) -> ee.Feature

.. py:function:: _lst_composite(start, end, period_ic, meta, reducer)

.. py:function:: _veg_composite(start, end, period_ic, meta, reducer)

.. py:function:: _chirps_composite(start, end, period_ic, meta, reducer)

.. py:data:: _COMPOSITE_BUILDERS

.. py:function:: _composite_image(product, start, end, period_ic, meta, reducer='mean')

.. py:function:: _empty_img(start: ee.Date, end: ee.Date, freq: str, prod: str) -> ee.Image

.. py:function:: _build_period_img(prod: str, r: str, start: ee.Date, end: ee.Date, period_ic: ee.ImageCollection, meta: Dict[str, Any], roi: Optional[ee.Geometry]) -> ee.Image

