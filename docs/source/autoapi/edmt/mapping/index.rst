edmt.mapping
============

.. py:module:: edmt.mapping


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/edmt/mapping/carto/index




Package Contents
----------------

.. py:function:: make_qr(url: str, label: str, short_url: str | None = None, size: int = 180, foreground: str = '#1B3A2D', background: str = 'white', muted: str = '#555555') -> PIL.Image.Image

   Generate a QR code image with a label and optional short URL.

   :param url: URL to encode in the QR code.
   :type url: str
   :param label: Title displayed below the QR code.
   :type label: str
   :param short_url: Shortened URL displayed below the label.
   :type short_url: str, optional
   :param size: Width and height of the QR code in pixels.
   :type size: int, default=180
   :param foreground: QR code and label color.
   :type foreground: str, default='#1B3A2D'
   :param background: Background color.
   :type background: str, default='white'
   :param muted: Color of the short URL text.
   :type muted: str, default='#555555'

   :returns: QR code image with annotations.
   :rtype: PIL.Image.Image


