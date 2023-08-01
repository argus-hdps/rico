.. Rico documentation master file, created by
   sphinx-quickstart on Tue May 23 21:45:58 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


******************
What is it?
******************

Rico is the data management system for the Evryscopes and the Argus Optical
Array. It provides tools for building and accessing data archives for
images, photometry, and transient alerts from both projects, as well as a
minimal user interface built around Slack. Within the transient alert
distribution scope, Rico includes functions for scalable cross-matching with
source catalogs and real-bogus vetting.

In the ecosystem of the Argus/Evryscope pipelines, Rico takes the data products
from Hera/Argus-HDPS/EFTE, stores them into the relevant data archives, and then
exports a user interface layer. Hera/Argus-HDPS/EFTE are the authors, Rico is
the librarian, and users and their programmatic tools are the readers.

  .. warning:: This project is under construction, and currently does not support full functionality or unauthenticated access. Public access is on the roadmap for the v1.0 release.


******************
How does it work? 
******************

Rico interfaces with several external data sinks to provide products to users,
including:

   1. Wasabi S3: Ancillary support products, including machine learning models
      and reference catalogs
   2. Kafka: Transient alerts, image metadata, weather data, and images. 




.. toctree::
   :maxdepth: 1
   :caption: Contents:

   install



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
