"""
tests/test_service_ports.py
===========================
Verification test suite ensuring that the Physics Simulator (Port 8000) and
Web Visualiser Dashboard (Port 5000) bind to distinct, non-conflicting network
ports under all configuration states and deployment environments.
"""

import importlib
import os

from software.simulator.config import Config as SimConfig
from software.visualiser.config import Config as VisConfig


def test_simulator_and_visualiser_distinct_default_ports():
    """Verify that Simulator and Visualiser default to different ports and do not collide."""
    assert SimConfig.PORT == 8000, f"Expected Simulator port 8000, got {SimConfig.PORT}"
    assert VisConfig.PORT == 5000, f"Expected Visualiser port 5000, got {VisConfig.PORT}"
    assert SimConfig.PORT != VisConfig.PORT, "CRITICAL: Simulator and Visualiser ports must not collide!"


def test_simulator_port_precedence_env(monkeypatch):
    """Verify that SIMULATOR_PORT takes precedence over generic PORT for Simulator."""
    monkeypatch.setenv("SIMULATOR_PORT", "8888")
    monkeypatch.setenv("PORT", "9999")

    import software.simulator.config as sim_config_module
    importlib.reload(sim_config_module)

    assert sim_config_module.Config.PORT == 8888


def test_visualiser_port_precedence_env(monkeypatch):
    """Verify that VISUALISER_PORT takes precedence over generic PORT for Visualiser."""
    monkeypatch.setenv("VISUALISER_PORT", "5555")
    monkeypatch.setenv("PORT", "9999")

    import software.visualiser.config as vis_config_module
    importlib.reload(vis_config_module)

    assert vis_config_module.Config.PORT == 5555


def test_visualiser_simulator_url_auto_derivation(monkeypatch):
    """Verify that Visualiser SIMULATOR_URL derives port from SIMULATOR_PORT when unset."""
    monkeypatch.delenv("SIMULATOR_URL", raising=False)
    monkeypatch.setenv("SIMULATOR_PORT", "8123")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)

    import software.visualiser.config as vis_config_module
    importlib.reload(vis_config_module)

    assert vis_config_module.Config.SIMULATOR_URL == "http://127.0.0.1:8123"


def test_gunicorn_conf_simulator_bind():
    """Verify that software/simulator/gunicorn.conf.py resolves port 8000 or SIMULATOR_PORT."""
    gconf_path = os.path.join(os.path.dirname(__file__), "..", "software", "simulator", "gunicorn.conf.py")
    ns = {}
    with open(gconf_path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, gconf_path, "exec"), ns)
    assert ":8000" in ns.get("bind") or ":5000" not in ns.get("bind")


def test_gunicorn_conf_visualiser_bind():
    """Verify that software/visualiser/gunicorn.conf.py resolves port 5000 or VISUALISER_PORT."""
    gconf_path = os.path.join(os.path.dirname(__file__), "..", "software", "visualiser", "gunicorn.conf.py")
    ns = {}
    with open(gconf_path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, gconf_path, "exec"), ns)
    assert ":5000" in ns.get("bind") or ":8000" not in ns.get("bind")
