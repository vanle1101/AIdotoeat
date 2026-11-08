"""Owner-only build and download endpoints for QA-gated product artifacts."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import FileResponse

from database import get_connection
from modules.product_builder import ProductBuilder, ProductBuildError

router = APIRouter()
STAGING_DIR = Path(__file__).resolve().parents[1] / "outputs" / "staging"


def _load_opportunity(opportunity_id: str) -> dict[str, Any]:
    if not opportunity_id or len(opportunity_id) > 120:
        raise HTTPException(status_code=422, detail="Opportunity id is invalid.")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT kind,status,payload_json FROM workflow_records WHERE id=?", (opportunity_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row or row["kind"] != "opportunity":
        raise HTTPException(status_code=404, detail="Source-backed opportunity was not found.")
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (TypeError, ValueError):
        raise HTTPException(status_code=409, detail="Opportunity record is malformed.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=409, detail="Opportunity record is malformed.")
    payload.setdefault("validation_status", row["status"])
    if str(payload.get("validation_status", "")).upper() != "VALIDATED_BY_SOURCE":
        raise HTTPException(status_code=409, detail="Opportunity is not VALIDATED_BY_SOURCE.")
    return payload


def _require_admin(request: Request) -> None:
    from workflow_api import _require_admin as require
    require(request)


@router.get("/api/product-studio/catalog")
def product_studio_catalog():
    from apps_library import product_studio_catalog as get_catalog
    catalog = get_catalog()
    staged_by_slug: dict[str, dict[str, Any]] = {}
    if STAGING_DIR.exists():
        for path in sorted(STAGING_DIR.glob("*.zip")):
            sidecar = path.with_suffix(path.suffix + ".sha256")
            if not sidecar.is_file():
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest not in sidecar.read_text(encoding="ascii", errors="ignore"):
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    manifest = json.loads(archive.read("BUILD_MANIFEST.json"))
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                continue
            if manifest.get("status") != "STAGING_QA_PASS" or not isinstance(manifest.get("quality_score"), (int, float)):
                continue
            for slug in manifest.get("included_app_slugs", []):
                if not isinstance(slug, str):
                    continue
                staged_by_slug[slug] = {
                    "quality_score": float(manifest["quality_score"]),
                    "quality_status": "STAGING_QA_PASS",
                    "artifact_id": path.stem,
                    "acceptance_test_count": len(manifest.get("acceptance_test_evidence", [])),
                }
    for item in catalog["items"]:
        evidence = staged_by_slug.get(item["slug"])
        if evidence and item["studio"].get("app_type"):
            item["studio"].update(evidence)
    return catalog


@router.post("/api/product-studio/build")
def build_product(request: Request, payload: dict[str, Any] = Body(...)):
    _require_admin(request)
    track = str(payload.get("track", "")).strip().lower()
    ids = payload.get("opportunity_ids")
    if isinstance(ids, str):
        ids = [ids]
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or any(not isinstance(item, str) for item in ids):
        raise HTTPException(status_code=422, detail="Provide one to three persisted opportunity ids.")
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Duplicate opportunity ids are not allowed.")
    opportunities = [_load_opportunity(item) for item in ids]
    try:
        if track in {"a", "service_audit", "service_pack"}:
            if payload.get("owner_permission_confirmed") is not True:
                raise HTTPException(status_code=422, detail="Confirm authorization to process this public site snapshot.")
            source_html = payload.get("source_html")
            if not isinstance(source_html, str) or len(source_html.encode("utf-8")) > 750_000:
                raise HTTPException(status_code=413, detail="Supply a UTF-8 HTML snapshot no larger than 750 KB.")
            label = str(payload.get("business_label") or "Owner-provided site snapshot")[:100]
            artifact = ProductBuilder.build_service_pack(opportunities[0], source_html,
                business_label=label, owner_permission_confirmed=True, staging_dir=STAGING_DIR)
        elif track in {"b", "data_workflow", "data_pack"}:
            artifact = ProductBuilder.build_data_workflow_pack(opportunities[0], staging_dir=STAGING_DIR)
        elif track in {"c", "microtool", "microtool_bundle"}:
            artifact = ProductBuilder.build_microtool_bundle(opportunities, staging_dir=STAGING_DIR)
        else:
            raise HTTPException(status_code=422, detail="Track must be A service pack, B data workflow, or C microtool bundle.")
    except ProductBuildError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "status": artifact.status, "artifact_id": artifact.artifact_id,
        "download_url": f"/api/product-studio/artifacts/{artifact.artifact_id}",
        "sha256": artifact.sha256, "quality_score": artifact.quality_score,
        "quality_score_method": artifact.manifest["quality_score_method"],
        "acceptance_results": [result.__dict__ for result in artifact.acceptance_results],
    }


def _artifact_path(artifact_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,159}", artifact_id):
        raise HTTPException(status_code=404, detail="Artifact not found.")
    root = STAGING_DIR.resolve()
    path = (root / f"{artifact_id}.zip").resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    return path


@router.get("/api/product-studio/artifacts")
def list_staged_artifacts(request: Request):
    _require_admin(request)
    items = []
    if not STAGING_DIR.exists():
        return {"items": [], "total": 0}
    for path in sorted(STAGING_DIR.glob("*.zip")):
        sidecar = path.with_suffix(path.suffix + ".sha256")
        if not sidecar.is_file():
            continue
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest not in sidecar.read_text(encoding="ascii", errors="ignore"):
            continue
        try:
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("BUILD_MANIFEST.json"))
        except (OSError, ValueError, KeyError, zipfile.BadZipFile):
            continue
        items.append({"artifact_id": path.stem, "file_name": path.name, "sha256": digest,
                      "quality_score": manifest.get("quality_score"), "status": manifest.get("status"),
                      "track": manifest.get("track"),
                      "acceptance_test_count": len(manifest.get("acceptance_test_evidence", [])),
                      "owner_final_review_required": bool(manifest.get("license_ip_check", {}).get("owner_final_review_required", True)),
                      "download_url": f"/api/product-studio/artifacts/{path.stem}"})
    return {"items": items, "total": len(items)}


@router.get("/api/product-studio/artifacts/{artifact_id}")
def download_staged_artifact(artifact_id: str, request: Request):
    _require_admin(request)
    path = _artifact_path(artifact_id)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise HTTPException(status_code=404, detail="Artifact integrity file not found.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest not in sidecar.read_text(encoding="ascii", errors="ignore"):
        raise HTTPException(status_code=409, detail="Artifact integrity check failed.")
    return FileResponse(path, media_type="application/zip", filename=path.name,
                        headers={"X-Artifact-SHA256": digest})
