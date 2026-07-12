from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from invyra_forecasting.api import tenant_context
from invyra_forecasting.data.repositories import FileSnapshotRepository


@contextmanager
def _tenant(tenant_id: str | None):
    token = tenant_context._TENANT_ID.set(tenant_context.normalize_tenant_id(tenant_id))
    try:
        yield
    finally:
        tenant_context._TENANT_ID.reset(token)


@dataclass(frozen=True)
class _Forecast:
    item_id: str


@dataclass(frozen=True)
class _Snapshot:
    snapshot_id: str
    forecast: _Forecast


def _snapshot(snapshot_id: str, item_id: str = "ITEM-001") -> _Snapshot:
    return _Snapshot(snapshot_id=snapshot_id, forecast=_Forecast(item_id=item_id))


def test_default_namespace_preserves_legacy_root_layout(tmp_path):
    repository = FileSnapshotRepository(tmp_path)

    with _tenant(None):
        path = repository.save(_snapshot("SNAP-DEFAULT"))

    assert path == tmp_path / "SNAP-DEFAULT.json"
    assert path.exists()


def test_named_tenants_use_isolated_snapshot_directories(tmp_path):
    repository = FileSnapshotRepository(tmp_path)

    with _tenant("alpha"):
        alpha_path = repository.save(_snapshot("SHARED-ID", item_id="ALPHA"))

    with _tenant("bravo"):
        bravo_path = repository.save(_snapshot("SHARED-ID", item_id="BRAVO"))

    assert alpha_path == tmp_path / "alpha" / "SHARED-ID.json"
    assert bravo_path == tmp_path / "bravo" / "SHARED-ID.json"
    assert alpha_path != bravo_path

    with _tenant("alpha"):
        assert repository.get("SHARED-ID")["forecast"]["item_id"] == "ALPHA"
        assert repository.list_snapshot_ids() == ["SHARED-ID"]

    with _tenant("bravo"):
        assert repository.get("SHARED-ID")["forecast"]["item_id"] == "BRAVO"
        assert repository.list_snapshot_ids() == ["SHARED-ID"]


def test_snapshot_is_not_visible_across_namespaces(tmp_path):
    repository = FileSnapshotRepository(tmp_path)

    with _tenant("alpha"):
        repository.save(_snapshot("ALPHA-ONLY"))
        assert repository.exists("ALPHA-ONLY")

    with _tenant("bravo"):
        assert repository.get("ALPHA-ONLY") is None
        assert not repository.exists("ALPHA-ONLY")
        assert repository.list_snapshot_ids() == []

    with _tenant(None):
        assert repository.get("ALPHA-ONLY") is None


def test_namespace_directory_encodes_path_separators(tmp_path):
    repository = FileSnapshotRepository(tmp_path)

    with _tenant("region/a"):
        path = repository.save(_snapshot("SAFE"))

    assert path == tmp_path / "region%2Fa" / "SAFE.json"
    assert path.is_file()
    assert not (tmp_path / "region" / "a" / "SAFE.json").exists()
