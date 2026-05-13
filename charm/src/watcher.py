"""Config watcher for Terrasquid - monitors DB config changes and reloads Squid."""
import json
import os
import sys
import time
from pathlib import Path

import psycopg

from squid import reload_squid, render_config, validate_config

DB_URL = os.environ.get("DATABASE_URL", "")
UNIT_NAME = os.environ.get("JUJU_UNIT_NAME", "terrasquid/0")
IS_LEADER = os.environ.get("JUJU_LEADER", "false").lower() == "true"
LOCAL_STATE_PATH = Path("/var/lib/terrasquid/state.json")
TEMPLATE_PATH = Path("/var/lib/terrasquid/templates/squid.conf.j2")
SQUID_CONF_PATH = Path("/etc/squid/conf.d/terrasquid.conf")
STAGING_CONF_PATH = Path("/etc/squid/conf.d/terrasquid.conf.staging")
POLL_INTERVAL = 5


def load_local_state() -> dict:
    """Load local unit state from disk."""
    if LOCAL_STATE_PATH.exists():
        return json.loads(LOCAL_STATE_PATH.read_text())
    return {
        "applied_config_version": 0,
        "last_reload": None,
        "last_reload_ok": True,
        "unit": UNIT_NAME,
    }


def save_local_state(state: dict) -> None:
    """Save local unit state to disk."""
    LOCAL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def render_and_validate(db_conn) -> tuple[str, bool]:
    """Get Squid config from DB (pre-rendered) or render from template."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version, rendered_config FROM terrasquid_api_configversion WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return "", False
        version, rendered = row

    if rendered:
        STAGING_CONF_PATH.write_text(rendered)
        if not validate_config(str(STAGING_CONF_PATH)):
            STAGING_CONF_PATH.unlink(missing_ok=True)
            return rendered, False
        STAGING_CONF_PATH.rename(SQUID_CONF_PATH)
        return rendered, True

    if IS_LEADER and TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text()
        context = build_context(db_conn)
        config = render_config(template, context)
        STAGING_CONF_PATH.write_text(config)
        if not validate_config(str(STAGING_CONF_PATH)):
            STAGING_CONF_PATH.unlink(missing_ok=True)
            return config, False
        STAGING_CONF_PATH.rename(SQUID_CONF_PATH)
        return config, True

    return "", False


def build_context(db_conn) -> dict:
    """Build template context from database state."""
    from types import SimpleNamespace

    with db_conn.cursor() as cur:
        cur.execute("SELECT id, service, name, cidr FROM terrasquid_api_sourceacl")
        source_rows = {r[0]: SimpleNamespace(id=r[0], service=r[1], name=r[2], cidr=r[3]) for r in cur.fetchall()}

        cur.execute("SELECT id, service, name FROM terrasquid_api_sourcegroup")
        source_group_rows = {r[0]: SimpleNamespace(id=r[0], service=r[1], name=r[2]) for r in cur.fetchall()}

        cur.execute("SELECT id, service, name, dst, type, ports FROM terrasquid_api_destinationconfig")
        dest_rows = {
            r[0]: SimpleNamespace(id=r[0], service=r[1], name=r[2], dst=r[3], type=r[4], ports=r[5])
            for r in cur.fetchall()
        }

        cur.execute("SELECT id, service, name FROM terrasquid_api_destinationgroup")
        dest_group_rows = {r[0]: SimpleNamespace(id=r[0], service=r[1], name=r[2]) for r in cur.fetchall()}

        cur.execute("SELECT id, service, name, ports FROM terrasquid_api_portgroup")
        port_groups = [
            SimpleNamespace(id=r[0], service=r[1], name=r[2], ports=r[3])
            for r in cur.fetchall()
        ]

        cur.execute(
            "SELECT sourcegroup_id, sourceacl_id FROM terrasquid_api_sourcegroup_sources"
        )
        for sg_id, src_id in cur.fetchall():
            sg = source_group_rows.get(sg_id)
            src = source_rows.get(src_id)
            if sg and src:
                if not hasattr(sg, "_sources"):
                    sg._sources = []
                sg._sources.append(src)

        cur.execute(
            "SELECT destinationgroup_id, destinationconfig_id FROM terrasquid_api_destinationgroup_destinations"
        )
        for dg_id, dst_id in cur.fetchall():
            dg = dest_group_rows.get(dg_id)
            dst = dest_rows.get(dst_id)
            if dg and dst:
                if not hasattr(dg, "_destinations"):
                    dg._destinations = []
                dg._destinations.append(dst)

        cur.execute(
            "SELECT service, priority, src_id, src_group_id, dst_id, dst_group_id "
            "FROM terrasquid_api_aclrule ORDER BY priority, created_at"
        )
        acl_rules = []
        for r in cur.fetchall():
            src = source_rows.get(r[2])
            src_group = source_group_rows.get(r[3])
            dst = dest_rows.get(r[4])
            dst_group = dest_group_rows.get(r[5])
            acl_rules.append(
                SimpleNamespace(
                    service=r[0],
                    priority=r[1],
                    src=src,
                    src_group=src_group,
                    dst=dst,
                    dst_group=dst_group,
                )
            )

    source_groups = []
    for sg in source_group_rows.values():
        sg.sources = SimpleNamespace(all=lambda sg=sg: getattr(sg, "_sources", []))
        source_groups.append(sg)

    destination_groups = []
    for dg in dest_group_rows.values():
        dg.destinations = SimpleNamespace(all=lambda dg=dg: getattr(dg, "_destinations", []))
        destination_groups.append(dg)

    return {
        "sources": list(source_rows.values()),
        "source_groups": source_groups,
        "destinations": list(dest_rows.values()),
        "destination_groups": destination_groups,
        "port_groups": port_groups,
        "acl_rules": acl_rules,
    }


def apply_config(db_conn, version: int) -> bool:
    """Render and apply Squid configuration."""
    config, ok = render_and_validate(db_conn)
    if not ok:
        return False

    if not SQUID_CONF_PATH.exists() or SQUID_CONF_PATH.read_text() != config:
        SQUID_CONF_PATH.write_text(config)

    result = reload_squid()
    success = result.returncode == 0

    state = load_local_state()
    state["applied_config_version"] = version if success else state.get("applied_config_version", 0)
    state["last_reload"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["last_reload_ok"] = success
    save_local_state(state)

    return success


def fetch_db_version(db_conn) -> int:
    """Fetch current config version from database."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT version FROM terrasquid_api_configversion WHERE id = 1")
        row = cur.fetchone()
        return row[0] if row else 0


def startup_recovery(db_conn) -> None:
    """On startup, compare DB version to local state and apply if DB is ahead."""
    db_version = fetch_db_version(db_conn)
    local_version = load_local_state().get("applied_config_version", 0)
    if db_version > local_version:
        apply_config(db_conn, db_version)


def listen_and_poll(db_url: str) -> None:
    """Connect to PostgreSQL, listen for notifications, and poll as fallback."""
    while True:
        try:
            with psycopg.connect(db_url) as conn:
                conn.autocommit = True
                startup_recovery(conn)

                with conn.cursor() as cur:
                    cur.execute("LISTEN terrasquid_config_changed")

                while True:
                    # Wait for notification or poll
                    notified = False
                    for notify in psycopg.waiting.wait(conn, timeout=POLL_INTERVAL * 1000):
                        if notify:
                            notified = True
                            break

                    if not notified:
                        # Poll fallback
                        current_version = fetch_db_version(conn)
                        local_version = load_local_state().get("applied_config_version", 0)
                        if current_version > local_version:
                            apply_config(conn, current_version)
                        continue

                    # Got notification
                    current_version = fetch_db_version(conn)
                    apply_config(conn, current_version)

        except psycopg.OperationalError:
            time.sleep(POLL_INTERVAL)
            continue


def main() -> None:
    """Main watcher entry point."""
    if not DB_URL:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    listen_and_poll(DB_URL)


if __name__ == "__main__":
    main()
