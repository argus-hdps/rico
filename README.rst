.. image:: images/logo.png
    :alt: Logo

.. container::

    |PyPI Status| |Documentation Status| |Pre-Commit| |isort Status| |black|


Rico: The Argus Optical Array Data Management System
====================================================

Images, light curves, and transient alerts from the Argus Optical Array and the Evryscopes.


Rico is a data access and management pipeline for the Argus Optical Array and
Evryscope projects, including internal and external use. This package contains both internal distribution systems and end-user access tools.

References
----------
Rico works primarily with data products from the Evryscope Fast Transient Engine (EFTE)
and the Argus Hierarchical Data Processing System (HDPS/Hera), which are described in
`Corbett+2023 <https://iopscience.iop.org/article/10.3847/1538-4365/acbd41#apjsacbd41s7>`_
and `Corbett+2022 <https://arxiv.org/abs/2207.14304>`_, respectively.

Prerequisites
-------------
This project currently requires pre-authentication with the project to access the alert
stream and data store. If you're interested in working with us, please reach
out!

Installation
------------
This project is distributed via PyPI as ``argus_rico``.

Roadmap and Status
==================

Rico is currently in an alpha state, and is currently being tested in ongoing transient
science programs with the Evryscopes. We expect to fully integrate with the
Argus Pathfinder alert stream later in 2023 in a 1.0 release.

See the `open issues <https://github.com/argus-hdps/rico/issues>`_ for a list of proposed features (and known issues).

License
-------
Distributed under the MIT License. See ``LICENSE`` for more information.

Contact
-------
Hank Corbett - htc@unc.edu

Project Link: `https://github.com/argus-hdps/rico`

.. |PyPI Status| image:: https://img.shields.io/pypi/v/argus_rico.svg
    :target: https://pypi.org/project/argus_rico
    :alt: Rico's PyPI Status

.. |Documentation Status| image:: https://readthedocs.org/projects/argus_rico/badge/?version=latest
   :target: http://rico.readthedocs.io/?badge=latest

.. |Pre-Commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

.. |isort Status| image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
    :target: https://pycqa.github.io/isort/
    :alt: isort Status

.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
