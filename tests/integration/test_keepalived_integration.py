import asyncio
import logging
import shlex
from pathlib import Path
import yaml

import pytest

log = logging.getLogger(__name__)


def _check_status_messages(ops_test):
    """Validate that the status messages are correct."""
    expected_messages = {
        "kubernetes-control-plane": "Kubernetes control-plane running.",
        "kubernetes-worker": "Kubernetes worker running.",
        "keepalived": "Please configure virtual ips",
    }
    for app, message in expected_messages.items():
        for unit in ops_test.model.applications[app].units:
            assert unit.workload_status_message == message


@pytest.mark.abort_on_fail
async def test_build_and_deploy(series, ops_test):
    log.info("Build Charm...")
    charm = await ops_test.build_charm("src")

    context = dict(charm=charm, series=series)
    overlays = [
        ops_test.Bundle("kubernetes-core", channel="edge"),
        Path("tests/data/bundle.yaml"),
    ]

    log.info("Build Bundle...")
    bundle, *overlays = await ops_test.async_render_bundles(*overlays, **context)

    log.info("Deploy Bundle...")
    model = ops_test.model_full_name
    cmd = f"juju deploy -m {model} {bundle} " + " ".join(
        f"--overlay={f}" for f in overlays
    )
    rc, stdout, stderr = await ops_test.run(*shlex.split(cmd))
    assert rc == 0, f"Bundle deploy failed: {(stderr or stdout).strip()}"

    log.info(stdout)
    await ops_test.model.block_until(
        lambda: "keepalived" in ops_test.model.applications, timeout=60
    )
    apps = [
        app
        for fragment in (bundle, *overlays)
        for app in yaml.safe_load(fragment.open())["applications"]
        if app != "keepalived"
    ]

    try:
        await asyncio.gather(
            ops_test.model.wait_for_idle(apps=["keepalived"], timeout=60 * 60),
            ops_test.model.wait_for_idle(
                apps=apps, wait_for_active=True, timeout=60 * 60
            ),
        )
    except asyncio.TimeoutError:
        if "kubernetes-control-plane" not in ops_test.model.applications:
            raise
        app = ops_test.model.applications["kubernetes-control-plane"]
        if not app.units:
            raise
        unit = app.units[0]
        if "kube-system pod" in unit.workload_status_message:
            log.debug(
                await juju_run(
                    unit, "kubectl --kubeconfig /root/.kube/config get all -A"
                )
            )
        raise
    _check_status_messages(ops_test)


async def juju_run(unit, cmd):
    result = await unit.run(cmd)
    code = result.results["Code"]
    stdout = result.results.get("Stdout")
    stderr = result.results.get("Stderr")
    assert code == "0", f"{cmd} failed ({code}): {stderr or stdout}"
    return stdout
