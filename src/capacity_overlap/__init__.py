"""capacity-overlap: the day-level over-allocation a sprint utilization bar cannot show.

The package is split so that the thing being critiqued (the sprint-level aggregate in
``sprintview``) and the thing that replaces it (the day-level load in ``overlap``) are
separate modules that can be compared directly in a test. The calendar module underneath
both exists because the whole result turns on counting working days, not calendar days.
"""

__version__ = "0.1.0"
