from __future__ import annotations

from .lamp_base import LampBase
from .lamp_geometry import LampGeometryMixin
from .lamp_contracts import LampContractsMixin


class TaskLampBuilder(LampGeometryMixin, LampContractsMixin, LampBase):
    pass
