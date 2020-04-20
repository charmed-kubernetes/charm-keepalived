from charmhelpers.core import hookenv, host  # patched

from reactive import keepalived as handlers


def test_series_upgrade():
    assert host.service_pause.call_count == 0
    assert host.service_resume.call_count == 0
    assert hookenv.status_set.call_count == 0
    handlers.pre_series_upgrade()
    assert host.service_pause.call_count == 2
    assert host.service_resume.call_count == 0
    assert hookenv.status_set.call_count == 1
    handlers.post_series_upgrade()
    assert host.service_pause.call_count == 2
    assert host.service_resume.call_count == 2
    assert hookenv.status_set.call_count == 1
