import pytest
from responses import RequestsMock


@pytest.fixture
def responses():
    with RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps
