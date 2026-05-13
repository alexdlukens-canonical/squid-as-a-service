"""Unit tests for the SquidAsAServiceCharm ops lifecycle."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import ops
import ops.testing
import pytest


@pytest.fixture(autouse=True)
def no_subprocess(monkeypatch):
    """Block all subprocess.run calls to prevent systemd/apt interactions during unit tests."""
    mock = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("subprocess.run", mock)
    return mock


@pytest.fixture()
def ctx():
    """Return an ops testing Context for SquidAsAServiceCharm."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from charm import SquidAsAServiceCharm

    return ops.testing.Context(SquidAsAServiceCharm)


@pytest.fixture()
def base_state():
    """Return a minimal State with no relations."""
    return ops.testing.State(
        config={
            "squid-port": 3128,
            "api-port": 8080,
            "gunicorn-workers": 4,
            "squid-extra-config": "",
        }
    )


class TestInstall:
    """Tests for the install event."""

    @patch("charm.SquidAsAServiceCharm._write_systemd_units")
    @patch("pathlib.Path.mkdir")
    def test_install_installs_squid(self, mock_mkdir, mock_units, no_subprocess, ctx, base_state):
        """The install event should trigger Squid installation."""
        with ctx(ctx.on.install(), base_state) as mgr:
            mgr.run()
        apt_calls = [c for c in no_subprocess.call_args_list if "apt-get" in str(c)]
        assert len(apt_calls) == 1

    @patch("charm.SquidAsAServiceCharm._write_systemd_units")
    @patch("pathlib.Path.mkdir")
    def test_install_writes_systemd_units(self, mock_mkdir, mock_units, ctx, base_state):
        """The install event should write systemd unit files."""
        with ctx(ctx.on.install(), base_state) as mgr:
            mgr.run()
        mock_units.assert_called_once()


class TestStart:
    """Tests for the start event."""

    def test_start_without_database_waits(self, ctx, base_state):
        """A start event with no database relation should set WaitingStatus."""
        with ctx(ctx.on.start(), base_state) as mgr:
            mgr.run()
            assert isinstance(mgr.charm.unit.status, ops.WaitingStatus)

    @patch("charm.SquidAsAServiceCharm._write_env_file")
    @patch("charm.SquidAsAServiceCharm._database_url", return_value="postgresql://u:p@host/db")
    def test_start_with_database_starts_services(self, mock_db, mock_env, no_subprocess, ctx, base_state):
        """A start event with a database should start all services."""
        with ctx(ctx.on.start(), base_state) as mgr:
            mgr.run()
        started = [str(c) for c in no_subprocess.call_args_list]
        assert any("enable" in s for s in started)


class TestDatabaseRelation:
    """Tests for database relation lifecycle."""

    @patch("charm.SquidAsAServiceCharm._start_services")
    @patch("charm.SquidAsAServiceCharm._run_manage")
    @patch("charm.SquidAsAServiceCharm._write_env_file")
    def test_database_created_runs_migrate(self, mock_env, mock_manage, mock_start, ctx, base_state):
        """database_created event should invoke migrate."""
        db_rel = ops.testing.Relation(
            "database",
            remote_app_name="postgresql",
            remote_app_data={
                "endpoints": "host:5432",
                "username": "usr",
                "password": "pwd",
                "database": "terrasquid",
            },
        )
        state = ops.testing.State(config=base_state.config, relations={db_rel})
        with ctx(ctx.on.relation_changed(db_rel), state) as mgr:
            mgr.run()
        mock_manage.assert_called_once_with("migrate", "--noinput")

    def test_database_relation_broken_stops_gunicorn(self, no_subprocess, ctx, base_state):
        """database_relation_broken should stop the Gunicorn service."""
        db_rel = ops.testing.Relation("database")
        state = ops.testing.State(config=base_state.config, relations={db_rel})
        with ctx(ctx.on.relation_broken(db_rel), state) as mgr:
            mgr.run()
        stopped = [str(c) for c in no_subprocess.call_args_list]
        assert any("stop" in s and "terrasquid-api" in s for s in stopped)


class TestCollectUnitStatus:
    """Tests for collect_unit_status event."""

    def test_no_database_reports_waiting(self, ctx, base_state):
        """Without a database relation the unit status should be Waiting."""
        with ctx(ctx.on.collect_unit_status(), base_state) as mgr:
            mgr.run()
            assert mgr.charm.unit.status == ops.WaitingStatus("Waiting for database relation")

    @patch("charm.SquidAsAServiceCharm._gunicorn_running", return_value=True)
    @patch("charm.SquidAsAServiceCharm._database_url", return_value="postgresql://u:p@host/db")
    def test_gunicorn_running_reports_active(self, mock_db, mock_guni, ctx, base_state):
        """With Gunicorn running the unit status should be Active."""
        with ctx(ctx.on.collect_unit_status(), base_state) as mgr:
            mgr.run()
            assert isinstance(mgr.charm.unit.status, ops.ActiveStatus)


class TestActions:
    """Tests for charm actions."""

    @patch("charm.SquidAsAServiceCharm._run_manage_capture", return_value=("key=abc\nprefix=ab12cd34\n", ""))
    def test_create_key_action_parses_output(self, mock_manage, ctx, base_state):
        """create-key action should return key and prefix from management command output."""
        with ctx(ctx.on.action("create-key", params={"name": "team-a"}), base_state) as mgr:
            mgr.run()

    @patch("charm.SquidAsAServiceCharm._run_manage_capture", return_value=("", "Error: key not found"))
    def test_create_key_action_fails_on_error(self, mock_manage, ctx, base_state):
        """create-key action should fail when the management command errors."""
        with pytest.raises(ops.testing.ActionFailed):
            with ctx(ctx.on.action("create-key", params={"name": "team-a"}), base_state) as mgr:
                mgr.run()

    @patch("squid.reload_squid", return_value=(True, ""))
    @patch("squid.write_squid_config")
    @patch("charm.SquidAsAServiceCharm._update_unit_status")
    @patch("charm.SquidAsAServiceCharm._db_config_version", return_value=3)
    @patch("charm.SquidAsAServiceCharm._run_manage_capture", return_value=("http_port 3128\n", ""))
    def test_reconfigure_action_reloads_squid(
        self, mock_manage, mock_version, mock_update_status, mock_write, mock_reload, ctx, base_state
    ):
        """Reconfigure action should write config and reload Squid."""
        with ctx(ctx.on.action("reconfigure"), base_state) as mgr:
            mgr.run()
        mock_write.assert_called_once()
        mock_reload.assert_called_once()


class TestEnvFile:
    """Tests for environment file generation."""

    @patch("charm.SquidAsAServiceCharm._get_or_generate_secret_key", return_value="s3cr3t")
    @patch("charm.SquidAsAServiceCharm._database_url", return_value="postgresql://u:p@db/terrasquid")
    def test_env_file_contains_database_url(self, mock_db, mock_key, ctx, base_state, tmp_path):
        """The env file should contain DATABASE_URL."""
        import charm as charm_module

        orig = charm_module.TERRASQUID_ENV_FILE
        charm_module.TERRASQUID_ENV_FILE = tmp_path / "terrasquid.env"
        try:
            with ctx(ctx.on.config_changed(), base_state) as mgr:
                mgr.run()
            content = (tmp_path / "terrasquid.env").read_text()
            assert "DATABASE_URL=postgresql://u:p@db/terrasquid" in content
        finally:
            charm_module.TERRASQUID_ENV_FILE = orig
