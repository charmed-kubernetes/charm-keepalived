from charmhelpers.core import host  # patched
from charms.layer import status  # patched

from reactive import keepalived as handlers


def test_series_upgrade():
    assert host.service_pause.call_count == 0
    assert host.service_resume.call_count == 0
    assert status.blocked.call_count == 0
    handlers.pre_series_upgrade()
    assert host.service_pause.call_count == 2
    assert host.service_resume.call_count == 0
    assert status.blocked.call_count == 1
    handlers.post_series_upgrade()
    assert host.service_pause.call_count == 2
    assert host.service_resume.call_count == 2
    assert status.blocked.call_count == 1
