************
Installation
************


Using ``pip``
=============
The simplest approach is just to install latest version from PyPI using ``pip``:
::

    pip install argus-rico

Rico requires Python 3.9+.  MacOS and Linux are the target platforms.

Using ``poetry``
================
If you want to hack on the codebase directly, you will need to first install
``poetry`` using the `standard installer
<https://python-poetry.org/docs/#installation>`_ provided by the Poetry
maintainers. 

1. Clone the repo::

    git clone git@github.com:argus-hdps/rico.git

2. Build the virtualenv and install dependencies::

    cd hera/
    poetry install

.. warning:: You will need to manually install ``qlsc`` when installing Rico with Poetry, due to a packaging conflict. 


1. Activate the environment::

    poetry shell




