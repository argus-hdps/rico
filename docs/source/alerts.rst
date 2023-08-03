.. _alerts: 

Transient Alerts
*********************************

Rico provides utilities for both generating and receiving transient
alerts. At the moment, EFTE alerts are available in real time from the
Evryscope-North. Alerts are streamed from the observatory as Avro packets, but
are easily decoded into JSON for analysis.

Alert Consumers
---------------

The simplest way to receive transient alerts is through the built-in command
line utility: 

    .. click:: argus_rico.cli:stream_json
        :prog: rico stream_json
        :nested: full
        :commands: stream_json

The ``stream_json`` subcommand of the ``rico`` utility continuously polls the
alert stream and records the results to JSON files to a local directory. 

Filtering Alerts
^^^^^^^^^^^^^^^
The alerts can be optionally filtered based on cross-match information prior to
being written to disk using a boolean filter defined in a text file. Each line
in the filter file should be formatted as ``PARAMETER`` ``OPERATOR`` ``VALUE``.
The ``PARAMETER`` can be anything included in the output of the ATLAS Refcat2
query (see :ref:`catalogs`), plus ``g-r``. 

The following is a simple filter for likely dM flares, selecting for alerts that
cross-match to nearby red stars\:

.. code-block:: text
    :caption: sample_filter.txt
    :linenos:

    g-r > 1.0
    parallax > 10


Setting Group ID
^^^^^^^^^^^^^^^^
Kafka enables load balancing of consumers for a topic by
splitting the incoming messages between multiple consumers with the same group
ID. Each consumer within the group is assigned a set of topic partitions and
will only receive the messages within its assigned partition. 

As a consequence of this, your consumer may not be assigned a partition if the
number of consumers in its group exceeds the number of partitions. To make sure
that you receive a full event stream, it is best to select a unique group ID. 

.. attention:: To make sure you receive all alerts, set a unique group ID for 
    your consumer.

Opening an Alert JSON
^^^^^^^^^^^^^^^^^^^^^^^

Alert JSON packets can be mapped to Python objects using Rico's
:ref:`data_models`, which are build with `Pydantic
<https://docs.pydantic.dev/latest/>`_. The following block shows how to read an
alert from disk with :class:`argus_rico.models.efte_alert.EFTEAlert` and access
its attributes.

.. code-block:: python
    :caption: Load a Rico EFTE Alert JSON
    :linenos:
    
    import argus_rico.models as arm

    alert = arm.EFTEAlert.from_json('438a94e5-2ffd-4b29-854d-7203e86dce8c.json')

The :class:`argus_rico.models.efte_alert.EFTEAlert` object is a Pydantic model
of the alert. The candidate itself is nested within the alert as an additional
model (:class:`argus_rico.models.efte_alert.EFTECandidate`), alongside a list of
potential crossmatches (:class:`argus_rico.models.efte_alert.XMatchItem`).

Internally, the image data around each candidate is stored in the
``stamp_bytes`` attribute of
:class:`argus_rico.models.efte_alert.EFTECandidate` as a BLOSC-compressed byte
array, but a standard Numpy version can be decoded on-the-fly by accessing the
``stamp`` attribute. The stamp array shape is (30,30,3). 

    .. automodule:: argus_rico.models.efte_alert
        :members: 
        :undoc-members:
        :show-inheritance:  




