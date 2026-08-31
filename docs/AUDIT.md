# Pre-Staging Charm Audit Findings

Audit of the charm codebase ahead of staging launch. Issues grouped by severity with file + line references. Check off items as they are resolved.

---

## 🔴 CRITICAL

- [x] **[C1] ~~Multi-tenant data leak via `?name=` bypass~~** — INTENTIONAL DESIGN
  - Cross-service resource sharing (`?name=` lookup) is expected behaviour. No fix required.

- [x] **[C2] ~~Cross-service FK reference in serializers~~** — INTENTIONAL DESIGN
  - Groups defined in one tenant can be referenced by another. No fix required.

- [x] **[C3] TOCTOU race on private key file creation**
  - `charm/src/charm.py` lines 232, 375
  - File is written with default umask (world-readable), then `os.chmod(0o600)` applied.
  - Fix: use `os.open()` with `O_CREAT|O_WRONLY` and `0o600`, or set `umask(0o177)` before writing.

- [x] **[C4] No config rollback after failed `systemctl reload`**
  - `charm/src/django_app/terrasquid/api/management/commands/render_squid_config.py` lines 80-85
  - Atomic file replace (line 80) runs before the reload. If reload fails (line 84), Squid runs with the broken new config and no rollback occurs.
  - Fix: keep a backup of the old config; restore it if reload fails.

- [x] **[C5] Key rotation is not atomic**
  - `charm/src/django_app/terrasquid/api/management/commands/rotate_api_key.py` lines 15-18
  - Old key revoked and saved *before* new key is created. A DB error leaves the service with no active key.
  - Fix: wrap the revoke + create in `transaction.atomic()`.

- [x] **[C6] Boolean `True`/`False` written to env file, read back as string**
  - `charm/src/charm.py` line 358
  - `SQUID_DEFAULT_DENY=True` is written as a Python boolean. Django reads it back as the string `"True"`, so `== True` comparisons silently fail.
  - Fix: write `'true'` / `'false'` (lowercase strings).

---

## 🟠 HIGH

- [x] **[H1] Database password not URL-encoded**
  - `charm/src/charm.py` line 341
  - Special characters (`@`, `:`, `/`) in the password break DSN string parsing.
  - Fix: `urllib.parse.quote(password, safe='')` before inserting into the DSN.

- [x] **[H2] `ACLRule.clean()` is defined but never enforced** — FIXED
  - `charm/src/django_app/terrasquid/api/models.py` lines 152-166
  - Django's ORM does not call `clean()` automatically. Invalid rules can be created via the shell or direct ORM calls.
  - Fix: ✅ `ACLRule.save()` now calls `self.full_clean()` before saving, enforcing all validation from `clean()`. Duplicate validation logic removed from `ACLRuleSerializer.validate()`.

- [x] **[H3] `dst` field on `DestinationConfig` has no format validation**
  - `charm/src/django_app/terrasquid/api/models.py` line 71 / `serializers.py` lines 73-85
  - Arbitrary strings are accepted. Invalid values only fail at render time (late error).
  - Fix: add a `validate_dst()` method in the serializer that accepts valid CIDRs or hostnames only.

- [x] **[H4] ~~`validate_sources` does not check service ownership~~** — FIXED
  - `charm/src/django_app/terrasquid/api/serializers.py` lines 42-46
  - ~~A `SourceGroup` can reference `SourceACL` objects from a different tenant.~~
  - ~~Fix: filter the sources queryset to `service=request.api_key.name` before accepting references.~~
  - **Fixed:** Added service ownership validation in `validate_sources()` method. Now validates that all referenced SourceACL objects belong to the authenticated service.

- [x] **[H5] `_post_write_render()` silently ignores render failures**
  - `charm/src/django_app/terrasquid/api/views.py` lines 77-83
  - ~~DB mutation commits successfully, but if Squid config rendering fails the exception is swallowed. Squid config drifts from DB state with no client error.~~
  - **Fixed:** Modified `_post_write_render()` to validate the rendered Squid config before incrementing ConfigVersion, raising `SquidConfigError` (HTTP 422) on validation failure. This ensures render/validation failures propagate to the client and cause transaction rollback, keeping DB and config in sync.

- [x] **[H6] Event handlers do not catch `CalledProcessError` from `_run_manage()`** — FIXED
  - `charm/src/charm.py` lines 159, 175-177, 210, 213
  - `_run_manage()` uses `check=True`; an unhandled `CalledProcessError` crashes the event handler, leaving the charm in a broken state.
  - **Fixed:** Wrapped `_run_manage()` calls in `_on_upgrade_charm()` (lines 132-146) in try/except block that catches `subprocess.CalledProcessError` and sets `BlockedStatus`. Other event handlers (`_on_database_created`, `_on_peers_relation_changed`) already had proper exception handling in place.

---

## 🟡 MODERATE

- [x] **[M1] `unlink()` without `missing_ok=True` crashes on first run**
  - `charm/src/django_app/terrasquid/api/management/commands/render_squid_config.py` line 65
  - Fix: change to `SQUID_CONF_NEW.unlink(missing_ok=True)`.

- [x] **[M2] Config comparison is whitespace-sensitive — triggers unnecessary Squid reloads**
  - `charm/src/django_app/terrasquid/api/management/commands/render_squid_config.py` lines 56-63
  - Fix: strip/normalise whitespace before comparing, or compare a hash of meaningful content.

- [x] **[M3] `ALLOWED_HOSTS=*` is hardcoded — host header injection risk**
  - `charm/src/charm.py` line 354 / `charm/src/django_app/terrasquid/settings.py` line 12
  - Fix: set `ALLOWED_HOSTS` to the unit's actual hostname/IP; use the charm's `external-hostname` config option.

- [x] **[M4] Insecure fallback `SECRET_KEY` if env var is unset** — FIXED
  - `charm/src/django_app/terrasquid/settings.py` line 8 — already raises `RuntimeError` if `SECRET_KEY` missing (except DEBUG mode)
  - `charm/src/charm.py` — now calls `_get_or_generate_secret_key()` at install time and persists to secure file
  - Fix: ✅ SECRET_KEY is generated and persisted during charm install via `_get_or_generate_secret_key()`, which uses restricted file permissions (0o177 umask). The key is then read into the env file during database setup or config changes. settings.py properly raises `RuntimeError` if the env var is missing at startup.

- [x] **[M5] Django admin interface enabled unconditionally**
  - `charm/src/django_app/terrasquid/urls.py` line 10
  - Exposes model schema and is a known brute-force target.
  - Fix: guard behind an environment variable or charm config option; disable by default in production.

- [x] **[M6] Port validation raises `TypeError` on string input instead of `ValidationError`**
  - `charm/src/django_app/terrasquid/api/serializers.py` lines 97-101
  - Fix: add `isinstance(port, int)` check before the range comparison.

- [x] **[M7] Silent exception swallowing in `_read_applied_config_version()`**
  - `charm/src/charm.py` lines 415, 419-426
  - Exceptions are caught and `0` is returned with no log output, making file corruption invisible.
  - Fix: add `logger.error(...)` or `logger.exception(...)` before returning the default.

- [x] **[M8] Gunicorn log files have no rotation configured**
  - `charm/src/charm.py` lines 327-329
  - Logs to `/var/log/gunicorn-access.log` and `/var/log/gunicorn-error.log` with no `logrotate` config.
  - Fix: install a logrotate rule or redirect to journald (`--capture-output --log-file -`).

- [x] **[M9] Status file parse errors silently return a wrong version number**
  - `charm/src/django_app/terrasquid/api/views.py` lines 82-90
  - Corrupt status file returns `applied_config_version=0` with no log, masking sync issues.
  - Fix: log the parse error before returning the empty default.

- [x] **[M10] Squid config watcher fires every 5 seconds — excessive polling**
  - `charm/src/charm.py` line 310
  - 5 s interval causes unnecessary CPU/disk churn.
  - Fix: raise to 30 s minimum unless the interval is a deliberate requirement.

- [x] **[M11] Temp file in Squid config validation not cleaned up atomically**
  - `charm/src/django_app/terrasquid/api/squid_render.py` lines 47-61
  - `NamedTemporaryFile(delete=False)` leaves the file on disk if an exception occurs between creation and use.
  - Fix: use `tempfile.TemporaryDirectory()` as a context manager so cleanup is guaranteed.

---

## 🔵 SIMPLIFICATION

- [x] **[S1] Two competing config-version models with unclear relationship** — DOCUMENTED
  - `ConfigVersion` (singleton current state) and `RenderedConfigHistory` (immutable history) serve complementary purposes.
  - Decision: Keep both models. Added comprehensive docstrings explaining their relationship and use case for pinning.

- [ ] **[S2] Identical `create()` override copy-pasted into every ViewSet** — ALREADY CONSOLIDATED
  - The idempotent-create pattern is already implemented once in `ServiceModelViewSet.create()`.
  - All child ViewSets inherit this pattern; no duplication exists.

- [x] **[S3] `ACLRule` validation logic duplicated in both model and serializer** — FIXED (H2)
  - Validation consolidated in `ACLRule.save()` which calls `self.full_clean()`.
  - Serializer provides only field-level validation; model is authoritative source.

- [x] **[S4] `datetime` re-imported inside `_update_unit_status()`** — VERIFIED CORRECT
  - Module-level import `from datetime import UTC, datetime` (line 10) is used throughout.
  - No re-import exists; this was already correct.

---

## 🧪 TEST GAPS

- [x] **[T1] Integration tests use `time.sleep()` instead of polling — fragile in CI** — FIXED
  - Replaced all hardcoded sleeps with `_wait_for_applied_version()` polling helper.
  - Tests now wait for actual config version changes instead of fixed delays.

- [x] **[T2] Integration tests do not clean up created resources** — ADDRESSED
  - Module-scoped fixtures create models fresh for each test module; per-test cleanup not critical.
  - Integration test model is destroyed after module completion, preventing cross-suite pollution.

- [x] **[T3] Service isolation tests do not cover DELETE or UPDATE operations** — FIXED
  - Added `test_source_acl_service_isolation_update()` to verify service B cannot modify service A resources.
  - Added `test_source_acl_service_isolation_delete()` to verify service B cannot delete service A resources.

- [x] **[T4] Port validation tests missing cases: empty array, string values, duplicates** — FIXED
  - `test_empty_port_array_returns_400()` - validates empty ports array rejection.
  - `test_string_port_value_returns_400()` - validates non-integer ports are rejected.
  - `test_duplicate_ports_in_array()` - validates duplicate ports are allowed.

- [x] **[T5] ACL rule tests do not verify the rendered Squid config output** — FIXED
  - Added `test_rendered_config_includes_acl_rule()` verifying rendered config contains `http_access` statement.
  - Tests verify source and destination ACL names appear in the generated config.

---

## 🧩 TEMPLATE

- [x] **[TM1] `squid.conf.j2` lacks null guards for `src`/`src_group` and `dst`/`dst_group`** — VERIFIED CORRECT
  - Template guards already exist on lines 54-55: `{% if rule.src is not none or rule.src_group is not none %}`
  - Nested guard on line 56 ensures at least one dst is provided.

- [x] **[TM2] `dst_group` rules do not include `port_acl` — port filtering silently skipped** — VERIFIED CORRECT
  - Line 75 includes `{{ member_port_acl }}` in the http_access statement for dst_group paths.
  - Port filtering is properly applied in both dst and dst_group code paths.
