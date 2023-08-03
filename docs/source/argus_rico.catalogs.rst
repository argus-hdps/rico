.. _catalogs: 
********************
Catalogs 
********************

This package contains wrappers for interacting with external reference catalogs.
At the moment, the only supported catalog is the `ATLAS All-Sky Stellar Reference
Catalog <https://ui.adsabs.harvard.edu/abs/2018ApJ...867..105T/abstract>`_ ("RefCat2"), a
widely available and well-characterized photometric resource with astrometry
flattened to Gaia DR2. 

.. important:: The ATLAS RefCat2 version distributed with Rico is a re-packaging of the 
   official product by the ATLAS team and omits many columns included in the original.
   We do not guarantee agreement beyond standard float precision, so please use with care. 

Please note that using these functions requires a local copy of the catalog,
which is retrievable from S3 with a Wasabi authentication key, but this requires
a significant amount of local storage (82 GB for the catalog, plus an additional
26 GB while decompressing from storage, **108 GB in total**). 

Usage
=====

If the catalog has not been previously used, you will be prompted to
install it the first time it's instantiated, so, be sure to run it somewhere
that user interaction is possible. 

.. code-block:: python

   import argus_rico.catalogs as arc

   atlas = arc.ATLASRefcat2()

You will then be prompted to confirm that you want to install the catalog:: 

   ATLAS RefCat not found, do you want to download it (82 GB)? [y/N]:

On confirmation, up to **108 GB** may be used temporarily, so make sure you have
space available. 

Once this download is complete, the :class:`~argus\_rico.catalogs.ATLASRefcat2`
object supports a simple radial query, which should take O(ms), depending on the
computer, storage, and radius. All angular arguments are in degrees, and
coordinates are assumed to be ICRS right ascension and declination. Query times
should be low, O(milliseconds) for 1 degree radii, increasing to O(seconds) at
O(10 degree) radii. 

.. note:: Rico does not support unit composition or conversion, as in Astropy; this is 
   motivated by performance requirements. 

.. code-block:: python

   sources = atlas.radial(123.45, 12.34, 1.0)

The output of the radial search can be either a Pandas DataFrame (default) or
the native storage format used by Rico catalogs (PyArrow table). The following
table shows a sample results table from a radial query.

.. list-table:: ATLAS Refcat2 Radial Query
   :widths: 5 5 7 5 5 3 5 5 5 5 5 5
   :header-rows: 1

   * - ra
     - dec
     - parallax
     - pmra
     - pmdec
     - g
     - r
     - i
     - h32
     - h64
     - h256
     - separation
   * - 123.000428
     - 11.70
     - 0.63
     - 2.41
     - 2.77
     - 15.00
     - 15.70
     - 15.59
     - 1154
     - 4617
     - 73874
     - 0.78
   * - 123.003187  
     - 11.774323      
     - 1.31   
     - 0.21  
     - -5.95 
     - 15.742 
     - 15.156
     - 14.926
     - 1154 
     - 4617 
     - 73875 
     - 0.714786




argus\_rico.catalogs API
============================

Submodules
----------

argus\_rico.catalogs.atlas module
---------------------------------

.. automodule:: argus_rico.catalogs.atlas
   :members:
   :undoc-members:
   :show-inheritance:

Module contents
---------------

.. automodule:: argus_rico.catalogs
   :members:
   :undoc-members:
   :show-inheritance:
