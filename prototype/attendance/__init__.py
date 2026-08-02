"""SAMS - Student Attendance Management System (implementation package).

Coursework prototype for CS402.3 Computer Graphics and Visualization.

The package is organised in layers:

======================  ====================================================
module                  responsibility
======================  ====================================================
:mod:`attendance.config`      tunable parameters, in one place
:mod:`attendance.imaging`     pure image-processing primitives
:mod:`attendance.table`       morphological table and grid reconstruction
:mod:`attendance.signature`   ink analysis and the present/absent decision
:mod:`attendance.stages`      the pipeline steps, as interchangeable objects
:mod:`attendance.pipeline`    orchestration and roster mapping
:mod:`attendance.progress`    progress presentation (console, windows, PNG stages)
:mod:`attendance.records`     ``info.xml`` parsing
:mod:`attendance.database`    SQLite persistence
:mod:`attendance.visualize`   attendance charts
:mod:`attendance.verify`      signature comparison
======================  ====================================================
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = [
    "config",
    "database",
    "imaging",
    "pipeline",
    "progress",
    "records",
    "signature",
    "stages",
    "table",
    "verify",
    "visualize",
]
