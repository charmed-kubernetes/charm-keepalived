import asyncio
import logging
import shlex
from pathlib import Path

import pytest
from pytest_operator.plugin import OpsTest

log = logging.getLogger(__name__)


def _check_status_messages(ops_test):
    """Validate that the status messages are correct."""
    expected_messages = {
        "kubernetes-control-plane": "Ready",
        "kubernetes-worker": "Ready",
        "keepalived": "Please configure virtual ips",
    }
    for app, message in expected_messages.items():
        for unit in ops_test.model.applications[app].units:
            assert unit.workload_status_message == message


@pytest.mark.abort_on_fail
async def test_build_and_deploy(series, ops_test: OpsTest):
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
    overlays = " ".join(f"--overlay={f}" for f in overlays)
    cmd = f"juju deploy -m {model} {bundle} {overlays}"
    await ops_test.run(*shlex.split(cmd), check=True, fail_msg="Bundle deploy failed")

    await ops_test.model.block_until(
        lambda: "keepalived" in ops_test.model.applications, timeout=60
    )
    apps = [app for app in ops_test.model.applications if app != "keepalived"]
    hour = 60 * 60

    try:
        await asyncio.gather(
            ops_test.model.wait_for_idle(apps=["keepalived"], timeout=hour),
            ops_test.model.wait_for_idle(apps=apps, status="active", timeout=hour),
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
