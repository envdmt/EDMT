edmt.mapping.carto
==================

.. py:module:: edmt.mapping.carto




Module Contents
---------------

.. py:function:: _load_font(name: str, size: int)

   Safely load a TrueType font with a fallback.


.. py:function:: make_qr(url: str, label: str, short_url: str | None = None, size: int = 180, foreground: str = '#1B3A2D', background: str = 'white', muted: str = '#555555') -> PIL.Image.Image

   Generate a QR code image with a label and optional short URL.

   Parameters
   ----------
   url : str
       URL to encode in the QR code.
   label : str
       Title displayed below the QR code.
   short_url : str, optional
       Shortened URL displayed below the label.
   size : int, default=180
       Width and height of the QR code in pixels.
   foreground : str, default='#1B3A2D'
       QR code and label color.
   background : str, default='white'
       Background color.
   muted : str, default='#555555'
       Color of the short URL text.

   Returns
   -------
   PIL.Image.Image
       QR code image with annotations.


