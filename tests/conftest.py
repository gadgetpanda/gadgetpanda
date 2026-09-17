import pytest

from gadgetpanda import Ring
from gadgetpanda.testing import FakeBleClient, SimulatedRing


@pytest.fixture
def firmware() -> SimulatedRing:
    return SimulatedRing()


@pytest.fixture
def ring(firmware: SimulatedRing) -> Ring:
    return Ring(firmware.advertised(), transport=FakeBleClient(firmware))
