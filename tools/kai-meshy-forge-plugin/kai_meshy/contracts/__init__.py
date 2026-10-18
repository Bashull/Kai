"""Offline, allowlisted Meshy contracts. A quote never grants authorization.

Auth, account/asset verification, persistent receipts and spending permission
belong to the existing Forge engine. This module performs no network or writes.
"""
from __future__ import annotations

import base64
import binascii
import copy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from ..core import ForgeError


class ContractError(ForgeError):
    """A safe machine code and known contract fields; never an input value."""

    def __init__(self, code, fields=()):
        self.code = code
        self.fields = tuple(fields)
        super().__init__(code + (":" + ",".join(self.fields) if self.fields else ""))


def _fail(code, *fields):
    raise ContractError(code, fields)


def _one(payload, fields):
    if sum(field in payload for field in fields) != 1:
        _fail("EXACTLY_ONE_INPUT_REQUIRED", *fields)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        _fail("NON_JSON_PARAMETERS")


def _context_row(row):
    if not isinstance(row, dict):
        _fail("INVALID_PARENT_CONTEXT")
    for key in ("operation_id", "status", "task_id", "ai_model", "model_type", "animation_type"):
        if row.get(key) is not None and not isinstance(row[key], str):
            _fail("INVALID_PARENT_CONTEXT")
    for key in ("account_verified", "assets_expired"):
        if key in row and not isinstance(row[key], bool):
            _fail("INVALID_PARENT_CONTEXT")
    if "candidate_ids" in row and (not isinstance(row["candidate_ids"], list) or any(not isinstance(c, str) for c in row["candidate_ids"])):
        _fail("INVALID_PARENT_CONTEXT")


def _day(value):
    try:
        return datetime.now(timezone.utc).date() if value is None else value.date() if isinstance(value, datetime) else value if isinstance(value, date) else date.fromisoformat(value)
    except (TypeError, ValueError):
        _fail("INVALID_AS_OF_DATE")


def _media(value, kind, field, maximum):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        # Base64 whitespace is normalized below, but URL control characters are forbidden.
        if not isinstance(value, str) or not value.startswith("data:"):
            _fail("INVALID_MEDIA_REFERENCE", field)
    if value.startswith("data:"):
        match = re.fullmatch(r"data:([^;,]+);base64,(.*)", value, re.S)
        if not match:
            _fail("INVALID_DATA_URI", field)
        mime, encoded = match.groups()
        if kind == "image" and mime.lower() not in {"image/png", "image/jpeg", "image/webp"}:
            _fail("UNSUPPORTED_IMAGE_MIME", field)
        if kind == "model" and not (mime.lower().startswith("model/") or mime.lower() in {"application/octet-stream", "application/fbx"}):
            _fail("UNSUPPORTED_MODEL_MIME", field)
        compact = re.sub(r"\s+", "", encoded)
        if len(compact) > 4 * ((maximum + 2) // 3):
            _fail("MEDIA_SIZE_LIMIT", field)
        try:
            data = base64.b64decode(compact, validate=True)
        except (ValueError, binascii.Error):
            _fail("INVALID_DATA_URI_BASE64", field)
        if not data or len(data) > maximum:
            _fail("MEDIA_SIZE_LIMIT", field)
        return {"media_sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "mime": mime.lower()}
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            _fail("INVALID_MEDIA_URL", field)
        _ = parsed.port
    except ValueError:
        _fail("INVALID_MEDIA_URL", field)
    # The caller's asset pipeline verifies URL reachability/size and allowed hosts.
    # Only its digest is included in a public quote, never the URL or query.
    return {"reference_sha256": hashlib.sha256(value.encode()).hexdigest()}


class CapabilityCatalog:
    """A frozen catalogue loaded independently of the process working directory."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(__file__).with_name("catalogue.json")
        try:
            raw = self.path.read_bytes()
            data = json.loads(raw)
            if data.get("schema") != "kai.meshy.capability-catalogue/v1" or not isinstance(data.get("operations"), dict):
                _fail("INVALID_CATALOGUE")
            for identifier, operation in data["operations"].items():
                if identifier != operation["id"] or not re.fullmatch(r"[a-z0-9_]+(?:\.[a-z0-9_]+)+", identifier):
                    _fail("INVALID_CATALOGUE_OPERATION")
                if operation["auth_family"] not in {"v1", "v2", "creative-lab"}:
                    _fail("INVALID_CATALOGUE_AUTH")
                for action, route in operation["routes"].items():
                    if not re.fullmatch(r"/openapi/(?:v[12]|creative-lab)/[a-z0-9_/{.}\-]+", route) or ".." in route:
                        _fail("INVALID_CATALOGUE_ROUTE")
                    if operation["route_methods"].get(action) != {"create": "POST", "get": "GET", "list": "GET", "stream": "GET", "cancel": "DELETE"}.get(action):
                        _fail("INVALID_CATALOGUE_METHOD")
                Draft202012Validator.check_schema(operation["request_schema"])
        except ContractError:
            raise
        except Exception:
            _fail("CATALOGUE_LOAD_FAILED")
        self._data = data
        self.contract_version = data["contract_version"]
        self.catalogue_sha256 = hashlib.sha256(raw).hexdigest()

    @classmethod
    def load(cls, path=None):
        return cls(path)

    @property
    def operations(self):
        return copy.deepcopy(self._data["operations"])

    def list(self):
        return [{"id": op["id"], "auth_family": op["auth_family"], "routes": copy.deepcopy(op["routes"]),
                 "paid": op["paid"], "price_rule": op["price"]["rule"], "contract_version": self.contract_version}
                for op in self._data["operations"].values()]

    def describe(self, operation_id):
        if not isinstance(operation_id, str) or operation_id not in self._data["operations"]:
            _fail("UNKNOWN_CAPABILITY")
        result = copy.deepcopy(self._data["operations"][operation_id])
        result["input_contract"] = copy.deepcopy(result["request_schema"])
        result["catalogue_sha256"] = self.catalogue_sha256
        result["sources"] = {name: copy.deepcopy(self._data["sources"][name]) for name in {
            result["source"].get("page"), result["source"].get("openapi"), result["price"]["source"],
            "meshy-changelog.md", "meshy-lifecycle.md", "meshy-retention.md"} if name}
        return result

    def _normalize(self, operation_id, parameters):
        if not isinstance(parameters, dict) or any(not isinstance(k, str) for k in parameters):
            _fail("PARAMETERS_MUST_BE_OBJECT")
        _canonical(parameters)
        p = copy.deepcopy(parameters)
        if operation_id.startswith("text_to_3d."):
            p.setdefault("mode", operation_id.rsplit(".", 1)[1])
        if operation_id == "creative_lab.keychain.prototype" and isinstance(p.get("name_text"), str):
            p["name_text"] = "".join(c for c in p["name_text"] if unicodedata.category(c) != "Cf").strip()
        if operation_id in {"text_to_3d.preview", "image_to_3d.generate", "multi_image_to_3d.generate"}:
            smart = p.get("model_type") == "smart-topology"
            p.setdefault("ai_model", "meshy-t2.5" if smart else "meshy-7.1")
            if p["ai_model"] == "latest":
                p["ai_model"] = "meshy-7.1"
        elif operation_id == "retexture.create":
            # Retexture's documented latest is Meshy7, unlike generation's7.1.
            p.setdefault("ai_model", "meshy-7")
            if p["ai_model"] == "latest":
                p["ai_model"] = "meshy-7"
        elif operation_id == "text_to_3d.refine" and p.get("ai_model") == "latest":
            p["ai_model"] = "meshy-7.1"
        if "hd_texture" in p and "texture_resolution" not in p and p["hd_texture"] is True:
            p["texture_resolution"] = "4k"
        if p.get("ultra_mode") is True:
            if p.get("geometry_resolution", "2k") != "2k":
                _fail("AMBIGUOUS_GEOMETRY_ALIAS", "ultra_mode", "geometry_resolution")
            p["geometry_resolution"] = "2k"
        return p

    def validate(self, operation_id, parameters, context=None, as_of=None):
        op = self.describe(operation_id)
        p = self._normalize(operation_id, parameters)
        if p.get("ai_model") == "meshy-5":
            _fail("MODEL_RETIRED", "ai_model")
        errors = sorted(Draft202012Validator(op["request_schema"]).iter_errors(p), key=lambda e: tuple(str(x) for x in e.path))
        if errors:
            error = errors[0]
            # Never include jsonschema.message (it contains rejected values).
            known = op["request_schema"]["properties"]
            path = tuple(str(x) for x in error.path if isinstance(x, int) or x in known)
            _fail("SCHEMA_" + error.validator.upper(), *path)
        if context is not None and not isinstance(context, dict):
            _fail("INVALID_CONTEXT")
        context = context or {}
        parent = context.get("parent", {})
        _context_row(parent)
        current_day = _day(as_of)
        source_fields = {"image_to_3d.generate": ("image_url", "input_task_id"), "multi_image_to_3d.generate": ("image_urls", "input_task_id"),
                         "image_to_image.generate": ("reference_image_urls", "input_task_id")}
        if operation_id in source_fields:
            _one(p, source_fields[operation_id])
        if "model_url" in op["request_schema"]["properties"]:
            _one(p, ("model_url", "input_task_id"))
        parents = context.get("parents", {})
        if not isinstance(parents, dict):
            _fail("INVALID_PARENTS_CONTEXT")
        for row in parents.values():
            _context_row(row)
        task_fields = [field for field, spec in op["input_fields"].items() if spec["kind"] == "task_id" and field in p]
        for field in task_fields:
            evidence = parents.get(field, parent if len(task_fields) == 1 else {})
            if not isinstance(evidence, dict):
                _fail("INVALID_PARENT_CONTEXT")
            allowed = op["input_fields"][field].get("allowed_parent_capabilities")
            if allowed and evidence.get("operation_id") is not None and evidence["operation_id"] not in allowed:
                _fail("PARENT_CAPABILITY_UNSUPPORTED", field)
            if evidence.get("status") not in {None, "SUCCEEDED"}:
                _fail("PARENT_NOT_SUCCEEDED", field)
            if evidence.get("task_id") not in {None, p[field]}:
                _fail("PARENT_TASK_MISMATCH", field)
            if evidence.get("account_verified") is False or evidence.get("assets_expired") is True:
                _fail("PARENT_UNVERIFIED_OR_EXPIRED", field)
        for field, spec in op["input_fields"].items():
            if field not in p or spec["kind"] not in {"image", "model"}:
                continue
            values = p[field] if spec.get("many") else [p[field]]
            for value in values:
                media = _media(value, spec["kind"], field, spec.get("data_uri_max_bytes", 20_000_000))
                if "mime" in media and media["mime"] not in spec.get("data_uri_mime_types", [media["mime"]]):
                    _fail("OPERATION_MEDIA_MIME_UNSUPPORTED", field)
                if spec.get("public_url_extensions") and not value.startswith("data:") and Path(urlsplit(value).path).suffix.lower() not in spec["public_url_extensions"]:
                    _fail("OPERATION_MODEL_FORMAT_UNSUPPORTED", field)

        generation = operation_id in {"text_to_3d.preview", "image_to_3d.generate", "multi_image_to_3d.generate"}
        model = p.get("ai_model") or parent.get("ai_model")
        if model == "latest":
            model = "meshy-7" if operation_id == "retexture.create" else "meshy-7.1"
        smart = p.get("model_type") == "smart-topology"
        lowpoly = p.get("model_type") == "lowpoly"
        if generation:
            if lowpoly and current_day >= date(2026, 10, 30):
                _fail("LOWPOLY_RETIRED", "model_type")
            if lowpoly and model == "meshy-6-lite":
                _fail("MODEL_CONFIGURATION_UNSUPPORTED", "ai_model", "model_type")
            if smart:
                if model not in {"meshy-t2", "meshy-t2.5"}:
                    _fail("SMART_MODEL_REQUIRED", "model_type", "ai_model")
                if p.get("topology", "triangle") != "triangle":
                    _fail("SMART_TRIANGLE_ONLY", "topology")
                if p.get("target_polycount", 0) > (15_000 if model == "meshy-t2" else 30_000):
                    _fail("SMART_POLYCOUNT_LIMIT", "target_polycount")
                p.setdefault("target_polycount", 4_000 if model == "meshy-t2" else 15_000)
            elif model in {"meshy-t2", "meshy-t2.5"}:
                _fail("SMART_MODEL_TYPE_REQUIRED", "model_type", "ai_model")
            if p.get("geometry_resolution", "standard") != "standard" and (model != "meshy-7.1" or lowpoly):
                _fail("GEOMETRY_MODEL_UNSUPPORTED", "geometry_resolution", "ai_model")
            if not smart and not lowpoly and "target_polycount" in p and "decimation_mode" not in p:
                remesh_default = model == "meshy-6-lite"
                if not p.get("should_remesh", remesh_default):
                    _fail("POLYCOUNT_REQUIRES_REMESH", "target_polycount", "should_remesh")
            if operation_id != "text_to_3d.preview":
                if (model == "meshy-6-lite" or smart) and any(f in p for f in ("image_enhancement", "remove_lighting")):
                    _fail("IMAGE_OPTIONS_MODEL_UNSUPPORTED", "image_enhancement", "remove_lighting")
                if "texture_image_urls" in p:
                    if not p["texture_image_urls"] or model != "meshy-7.1":
                        _fail("TEXTURE_VIEWS_MODEL_UNSUPPORTED", "texture_image_urls", "ai_model")
                    if "texture_image_url" in p or "texture_prompt" in p or p.get("should_texture") is False:
                        _fail("AMBIGUOUS_TEXTURE_REFERENCE", "texture_image_url", "texture_image_urls", "texture_prompt", "should_texture")
        texturing = operation_id in {"text_to_3d.refine", "retexture.create"} or (generation and operation_id != "text_to_3d.preview" and p.get("should_texture", True))
        resolution = p.get("texture_resolution", "2k")
        if texturing and resolution != "2k" and model == "meshy-6-lite":
            _fail("TEXTURE_MODEL_UNSUPPORTED", "texture_resolution", "ai_model")
        if operation_id == "text_to_3d.refine":
            if resolution != "2k" and model in {"meshy-t2", "meshy-t2.5", "meshy-7"}:
                _fail("REFINE_TEXTURE_MODEL_UNSUPPORTED", "texture_resolution", "ai_model")
            if "remove_lighting" in p and model == "meshy-6-lite":
                _fail("LIGHTING_MODEL_UNSUPPORTED", "remove_lighting", "ai_model")
        if operation_id == "retexture.create":
            _one(p, ("text_style_prompt", "image_style_url", "multiview_image_urls"))
            if "multiview_image_urls" in p and parameters.get("ai_model") != "meshy-7":
                _fail("MULTIVIEW_EXPLICIT_MODEL_REQUIRED", "multiview_image_urls", "ai_model")
            if "remove_lighting" in p and model == "meshy-6-lite":
                _fail("LIGHTING_MODEL_UNSUPPORTED", "remove_lighting", "ai_model")
        if operation_id == "resize.create":
            dimensions = sum(f in p for f in ("resize_height", "resize_longest_side")) + (p.get("auto_size") is True)
            if dimensions != 1:
                _fail("EXACTLY_ONE_RESIZE_MODE", "resize_height", "resize_longest_side", "auto_size")
            if any(p.get(f, 1) <= 0 for f in ("resize_height", "resize_longest_side")):
                _fail("POSITIVE_RESIZE_REQUIRED", "resize_height", "resize_longest_side")
        if operation_id == "remesh.create" and any(f in p for f in ("resize_height", "resize_longest_side")):
            _fail("DEPRECATED_REMESH_RESIZE_USE_RESIZE_OPERATION", "resize_height", "resize_longest_side")
        if operation_id == "remesh.create" and p.get("convert_format_only") is True:
            _fail("DEPRECATED_REMESH_CONVERT_USE_CONVERT_OPERATION", "convert_format_only")
        if operation_id == "animation.create":
            _one(p, ("action_id", "action_ids", "motion_task_id"))
            post = p.get("post_process", {})
            if "fps" in post and post.get("operation_type") != "change_fps":
                _fail("FPS_REQUIRES_CHANGE_FPS", "post_process")
            if "motion_task_id" in p and parent.get("animation_type") not in {None, "biped"}:
                _fail("MOTION_RETARGET_BIPED_ONLY", "motion_task_id")
        if operation_id in {"text_to_image.generate", "image_to_image.generate"}:
            if p.get("generate_multi_view") and "aspect_ratio" in p:
                _fail("MULTIVIEW_ASPECT_CONFLICT", "generate_multi_view", "aspect_ratio")
            if p.get("aspect_ratio") in {"3:2", "2:3"} and not model.startswith("gpt-image-"):
                _fail("ASPECT_GPT_ONLY", "aspect_ratio", "ai_model")
        if operation_id in {"print.analyze", "print.repair"}:
            if "intended_print_height_mm" in p and "intended_print_longest_side_mm" in p:
                _fail("PRINT_DIMENSIONS_EXCLUSIVE", "intended_print_height_mm", "intended_print_longest_side_mm")
            if "intended_print_height_mm" in p and "model_url" in p and not self._is_glb(p["model_url"]):
                _fail("PRINT_HEIGHT_REQUIRES_GLB", "model_url")
        if operation_id == "print.multi_color" and "model_url" in p:
            value = p["model_url"]
            if value.startswith("data:") and not self._is_glb(value):
                _fail("MULTICOLOR_DATA_REQUIRES_GLB", "model_url")
            if not value.startswith("data:") and Path(urlsplit(value).path).suffix.lower() not in {".glb", ".fbx"}:
                _fail("MULTICOLOR_REQUIRES_GLB_OR_FBX", "model_url")
        if operation_id == "print.auto_split":
            if p.get("mode", "auto") != "auto" and not p.get("prompt", "").strip():
                _fail("SPLIT_MODE_REQUIRES_PROMPT", "mode", "prompt")
            if any(f in p for f in ("connector_type", "connector_size", "connector_height")) and not p.get("connectors"):
                _fail("CONNECTOR_OPTIONS_REQUIRE_ENABLE", "connectors")
            if parent.get("ai_model") in {"meshy-6-lite", "meshy-t2", "meshy-t2.5"} or parent.get("model_type") in {"lowpoly", "smart-topology"}:
                _fail("SPLIT_PARENT_MODEL_UNSUPPORTED", "input_task_id")
            if p.get("mode") == "by_color" and parent.get("operation_id") not in {None, "image_to_3d.generate", "multi_image_to_3d.generate"}:
                _fail("SPLIT_COLOR_REQUIRES_IMAGE_PARENT", "input_task_id")
        if operation_id == "creative_lab.fidget_pixel.build":
            options = p.get("options", {})
            if options.get("shape", "square") == "hex" and options.get("piece_size_mm", 8) == 10:
                _fail("HEX_PIECE_SIZE_UNSUPPORTED", "options")
        constraints = op["parent_constraints"]
        if constraints:
            if parent.get("operation_id") not in {None, constraints.get("operation_id")}:
                _fail("PARENT_PRODUCT_MISMATCH", "input_task_id")
            if parent.get("status") not in {None, "SUCCEEDED"}:
                _fail("PARENT_NOT_SUCCEEDED", "input_task_id")
            if parent.get("account_verified") is False:
                _fail("PARENT_ACCOUNT_NOT_VERIFIED", "input_task_id")
            if parent.get("task_id") not in {None, p.get("input_task_id")}:
                _fail("PARENT_TASK_MISMATCH", "input_task_id")
            if "candidate_id" in p and "candidate_ids" in parent and p["candidate_id"] not in parent["candidate_ids"]:
                _fail("CANDIDATE_NOT_IN_PARENT", "candidate_id")
        return p

    @staticmethod
    def _is_glb(value):
        return value.lower().startswith("data:model/gltf-binary;base64,") or (not value.startswith("data:") and Path(urlsplit(value).path).suffix.lower() == ".glb")

    def _fingerprint(self, operation_id, p):
        safe = copy.deepcopy(p)
        op = self._data["operations"][operation_id]
        for field, spec in op["input_fields"].items():
            if field not in safe or spec["kind"] not in {"image", "model"}:
                continue
            values = safe[field] if spec.get("many") else [safe[field]]
            hashed = [_media(v, spec["kind"], field, spec.get("data_uri_max_bytes", 20_000_000)) for v in values]
            safe[field] = hashed if spec.get("many") else hashed[0]
        return hashlib.sha256(_canonical({"operation_id": operation_id, "contract_version": self.contract_version, "catalogue_sha256": self.catalogue_sha256, "parameters": safe}).encode()).hexdigest()

    def validation_report(self, operation_id, parameters, context=None, as_of=None):
        p = self.validate(operation_id, parameters, context, as_of)
        return {"valid": True, "operation_id": operation_id, "contract_version": self.contract_version,
                "payload_fingerprint": self._fingerprint(operation_id, p), "fields": sorted(p),
                "warnings": self._warnings(operation_id, p), "authorization": "NOT_GRANTED_BY_CATALOGUE"}

    @staticmethod
    def _warnings(operation_id, p):
        result = []
        if p.get("model_type") == "lowpoly":
            result.append("LOWPOLY_DEPRECATED_RETIREMENT_2026_10_30_IGNORED_MODEL_OPTIONS")
        if p.get("ai_model") == "meshy-7":
            result.append("LEGACY_MESHY7_GENERATION_MODEL" if operation_id != "retexture.create" else "RETEXTURE_LATEST_RESOLVES_MESHY7")
        if "hd_texture" in p:
            result.append("HD_TEXTURE_DEPRECATED_EXPLICIT_RESOLUTION_TAKES_PRECEDENCE")
        if "ultra_mode" in p:
            result.append("ULTRA_MODE_DEPRECATED")
        if operation_id.startswith("creative_lab.") and operation_id.endswith(".build"):
            result.append("HUMAN_VISUAL_APPROVAL_AND_VERIFIED_PARENT_REQUIRED_BEFORE_SUBMIT")
        if operation_id in {"text_to_image.generate", "image_to_image.generate"} and p.get("pose_mode") and p.get("ai_model") in {"nano-banana", "nano-banana-pro"}:
            result.append("POSE_EFFECTIVE_NANO_BANANA_PRO_REQUIRES_PRO_ACCOUNT")
        return result

    def quote(self, operation_id, parameters, context=None, as_of=None):
        p = self.validate(operation_id, parameters, context, as_of)
        op = self._data["operations"][operation_id]
        rule = op["price"]["rule"]
        model = p.get("ai_model") or (context or {}).get("parent", {}).get("ai_model")
        credits, reason = None, "UNRESOLVED_PRICE"
        if rule == "fixed":
            credits = op["price"]["parameters"]["credits"]
        elif rule == "free":
            credits = 0
        elif rule in {"generation_mesh", "generation_textured"}:
            effective = "meshy-6" if p.get("model_type") == "lowpoly" else model
            credits = 5 if effective in {"meshy-6-lite", "meshy-t2", "meshy-t2.5"} else 20
            if rule == "generation_textured" and p.get("should_texture", True):
                credits += 15 if p.get("texture_resolution") == "8k" else 10
            if p.get("geometry_resolution", "standard") != "standard":
                credits += 5
        elif rule == "texture":
            if operation_id == "text_to_3d.refine" and p.get("texture_resolution", "2k") != "2k" and model not in {"meshy-6", "meshy-7.1", "latest"}:
                reason = "REFINE_PARENT_MODEL_UNVERIFIED_FOR_HIGH_RESOLUTION"
            else:
                credits = 15 if p.get("texture_resolution") == "8k" else 10
        elif rule == "animation":
            if "motion_task_id" in p:
                reason = "MOTION_RETARGET_PRICE_NOT_PUBLISHED"
            else:
                credits = 3 * len(p.get("action_ids", [p.get("action_id")]))
        elif rule == "motion":
            credits = 3 if p.get("mode", "prime") == "swift" else 10
        elif rule == "image_generation":
            effective = "nano-banana-pro" if p.get("pose_mode") and model in {"nano-banana", "nano-banana-pro"} else model
            if effective.startswith("gpt-image-"):
                credits = 12 if operation_id == "image_to_image.generate" else 9
            else:
                credits = {"nano-banana": 3, "nano-banana-2": 6, "nano-banana-2-lite": 3, "nano-banana-pro": 9}.get(effective)
        documentary_credits = credits
        checked = date.fromisoformat(op["price"]["source_checked_date_utc"])
        evaluation = _day(as_of)
        expiry = checked + timedelta(days=min(op["price"].get("maximum_age_days", 7), 7))
        source_fresh = checked <= evaluation < expiry
        if not source_fresh:
            credits, reason = None, "PRICE_SOURCE_STALE_OR_EVALUATION_PRECEDES_SOURCE"
        exact = isinstance(credits, int) and credits >= 0
        return {"operation_id": operation_id, "credits": credits if exact else None, "price_status": "EXACT" if exact else "UNKNOWN",
                "spend_allowed": exact, "spend_allowed_scope": "PRICING_GATE_ONLY_NOT_PERMISSION", "authorization": "NOT_GRANTED_BY_CATALOGUE",
                "documentary_credits": documentary_credits, "source_fresh": source_fresh,
                "evaluated_date_utc": evaluation.isoformat(), "source_checked_date_utc": checked.isoformat(),
                "price_expires_at_utc": expiry.isoformat() + "T00:00:00Z",
                "reason": "OFFICIAL_PUBLISHED_PRICE_RULE" if exact else reason, "price_source": copy.deepcopy(self._data["sources"][op["price"]["source"]]),
                "contract_version": self.contract_version, "catalogue_sha256": self.catalogue_sha256,
                "payload_fingerprint": self._fingerprint(operation_id, p), "warnings": self._warnings(operation_id, p)}


__all__ = ["CapabilityCatalog", "ContractError"]
