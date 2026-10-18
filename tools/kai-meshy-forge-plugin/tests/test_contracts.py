"""Offline policy regressions against bundled, provenance-pinned contracts."""
import base64
import copy
from datetime import date
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kai_meshy.contracts import CapabilityCatalog, ContractError
from kai_meshy.core import ForgeError


IMAGE = "https://example.invalid/reference.png"
MODEL = "https://example.invalid/model.glb"
TASK = "01a15090-2515-7561-99e8-14def9e4b0ea"


def minimum_payload(identifier):
    if identifier == "text_to_3d.preview":
        return {"prompt": "A grey humanoid figure"}
    if identifier == "text_to_3d.refine":
        return {"preview_task_id": TASK}
    if identifier == "image_to_3d.generate":
        return {"image_url": IMAGE}
    if identifier == "multi_image_to_3d.generate":
        return {"image_urls": [IMAGE]}
    if identifier == "convert.create":
        return {"model_url": MODEL, "target_formats": ["obj"]}
    if identifier == "resize.create":
        return {"model_url": MODEL, "resize_height": 1.5}
    if identifier == "retexture.create":
        return {"model_url": MODEL, "text_style_prompt": "Grey skin"}
    if identifier == "animation.create":
        return {"rig_task_id": TASK, "action_id": 0}
    if identifier in {"text_to_image.generate", "image_to_image.generate"}:
        p = {"ai_model": "nano-banana", "prompt": "A grey humanoid figure"}
        if identifier.startswith("image_"):
            p["reference_image_urls"] = [IMAGE]
        return p
    if identifier == "text_to_motion.generate":
        return {"prompt": "Walk forwards", "duration": 4}
    if identifier == "print.auto_split":
        return {"input_task_id": TASK}
    if identifier.startswith("creative_lab."):
        if identifier.endswith(".build"):
            return {"input_task_id": TASK, **({"candidate_id": "candidate-a"} if ".keycap." in identifier else {})}
        return {"image_url": IMAGE, **({"type": "person"} if ".fidget_pixel." in identifier else {})}
    return {"model_url": MODEL}


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = CapabilityCatalog.load()

    def assert_rejected(self, capability, parameters, code=None, **kw):
        with self.assertRaises(ContractError) as caught:
            self.catalog.validate(capability, parameters, **kw)
        self.assertIsInstance(caught.exception, ForgeError)
        if code:
            self.assertEqual(caught.exception.code, code)
        return str(caught.exception)

    def test_all_35_operations_have_typed_allowlisted_routes_and_minimum_quote(self):
        operations = self.catalog.list()
        self.assertEqual(len(operations), 35)
        for item in operations:
            with self.subTest(item["id"]):
                op = self.catalog.describe(item["id"])
                self.assertTrue(op["routes"]["create"].startswith("/openapi/"))
                self.assertEqual(op["route_methods"]["create"], "POST")
                self.assertEqual(op["route_methods"]["get"], "GET")
                self.assertEqual(op["route_methods"]["list"], "GET")
                self.assertEqual(op["input_contract"], op["request_schema"])
                self.assertFalse(op["request_schema"]["additionalProperties"])
                self.assertTrue(all(len(s["sha256"]) == 64 for s in op["sources"].values()))
                p = minimum_payload(item["id"])
                q = self.catalog.quote(item["id"], p, as_of="2026-10-18")
                self.assertEqual(q["price_status"], "EXACT")
                self.assertIsInstance(q["credits"], int)
                self.assertEqual(q["authorization"], "NOT_GRANTED_BY_CATALOGUE")

    def test_read_copy_cannot_change_future_contracts(self):
        op = self.catalog.describe("image_to_3d.generate")
        op["request_schema"]["additionalProperties"] = True
        self.catalog.operations.clear()
        self.assertEqual(len(self.catalog.list()), 35)
        self.assert_rejected("image_to_3d.generate", {"image_url": IMAGE, "unknown": True})

    def test_unknown_operation_is_never_interpreted_as_route(self):
        self.assert_rejected("https://attacker.invalid/POST", {})

    def test_unknown_fields_at_both_levels_are_rejected_without_echoing_secrets(self):
        message = self.assert_rejected("creative_lab.lamp.build", {"input_task_id": TASK, "options": {"secret-private-value": "msy_do_not_echo"}})
        self.assertNotIn("secret-private-value", message)
        self.assertNotIn("msy_", message)
        self.assert_rejected("image_to_3d.generate", {"image_url": IMAGE, "api_key": "msy_do_not_echo"})

    def test_every_model_source_requires_exactly_one(self):
        for operation in ["image_to_3d.generate", "multi_image_to_3d.generate", "image_to_image.generate", "remesh.create", "convert.create", "resize.create", "uv_unwrap.create", "retexture.create", "rigging.create", "print.analyze", "print.repair", "print.multi_color"]:
            with self.subTest(operation):
                p = minimum_payload(operation)
                source = next(k for k in p if k in {"model_url", "image_url", "image_urls", "reference_image_urls"})
                p["input_task_id"] = TASK
                self.assert_rejected(operation, p, "EXACTLY_ONE_INPUT_REQUIRED")
                del p["input_task_id"]; del p[source]
                self.assert_rejected(operation, p, "EXACTLY_ONE_INPUT_REQUIRED")

    def test_refine_is_distinct_from_preview_and_does_not_default_inheritance_away(self):
        p = self.catalog.validate("text_to_3d.refine", {"preview_task_id": TASK})
        self.assertEqual(p, {"mode": "refine", "preview_task_id": TASK})
        self.assert_rejected("text_to_3d.refine", {"preview_task_id": TASK, "prompt": "wrong stage"})
        self.assert_rejected("text_to_3d.preview", {"prompt": "figure", "mode": "fused"})
        self.assert_rejected("text_to_3d.refine", {"preview_task_id": TASK, "ai_model": "meshy-t2.5"})

    def test_endpoint_specific_latest_does_not_drift(self):
        self.assertEqual(self.catalog.validate("image_to_3d.generate", {"image_url": IMAGE, "ai_model": "latest"})["ai_model"], "meshy-7.1")
        self.assertEqual(self.catalog.validate("retexture.create", {"model_url": MODEL, "text_style_prompt": "stone", "ai_model": "latest"})["ai_model"], "meshy-7")

    def test_smart_topology_default_ranges_and_triangle_constraint(self):
        for model, default, maximum in [("meshy-t2", 4000, 15000), ("meshy-t2.5", 15000, 30000)]:
            p = {"prompt": "figure", "model_type": "smart-topology", "ai_model": model}
            self.assertEqual(self.catalog.validate("text_to_3d.preview", p)["target_polycount"], default)
            self.assertEqual(self.catalog.quote("text_to_3d.preview", p)["credits"], 5)
            self.assert_rejected("text_to_3d.preview", {**p, "target_polycount": maximum + 1}, "SMART_POLYCOUNT_LIMIT")
            self.assert_rejected("text_to_3d.preview", {**p, "topology": "quad"}, "SMART_TRIANGLE_ONLY")
        p = self.catalog.validate("text_to_3d.preview", {"prompt": "figure", "model_type": "smart-topology"})
        self.assertEqual(p["ai_model"], "meshy-t2.5")
        self.assert_rejected("text_to_3d.preview", {"prompt": "figure", "ai_model": "meshy-t2.5"}, "SMART_MODEL_TYPE_REQUIRED")

    def test_lowpoly_retirement_and_meshy5_retired(self):
        p = {"prompt": "figure", "model_type": "lowpoly"}
        q = self.catalog.quote("text_to_3d.preview", p, as_of="2026-10-29")
        self.assertEqual(q["documentary_credits"], 20)
        self.assertEqual(q["price_status"], "UNKNOWN")
        self.assertTrue(q["warnings"])
        self.assert_rejected("text_to_3d.preview", p, "LOWPOLY_RETIRED", as_of="2026-10-30")
        self.assert_rejected("text_to_3d.preview", {"prompt": "figure", "ai_model": "meshy-5"}, "MODEL_RETIRED")

    def test_generation_price_cells_and_ultra_surcharge(self):
        for model, mesh in [("meshy-7.1", 20), ("meshy-7", 20), ("meshy-6", 20), ("meshy-6-lite", 5), ("meshy-t2", 5), ("meshy-t2.5", 5)]:
            p = {"image_url": IMAGE, "ai_model": model}
            if model.startswith("meshy-t"):
                p["model_type"] = "smart-topology"
            self.assertEqual(self.catalog.quote("image_to_3d.generate", {**p, "should_texture": False})["credits"], mesh)
            for res, addition in [("2k", 10), ("4k", 10), ("8k", 15)]:
                with self.subTest(model=model, texture=res):
                    if model == "meshy-6-lite" and res != "2k":
                        self.assert_rejected("image_to_3d.generate", {**p, "texture_resolution": res})
                    else:
                        self.assertEqual(self.catalog.quote("image_to_3d.generate", {**p, "texture_resolution": res})["credits"], mesh + addition)
        self.assertEqual(self.catalog.quote("image_to_3d.generate", {"image_url": IMAGE, "geometry_resolution": "4k"})["credits"], 35)
        self.assert_rejected("multi_image_to_3d.generate", {"image_urls": [IMAGE], "geometry_resolution": "4k"})
        self.assert_rejected("image_to_3d.generate", {"image_url": IMAGE, "ai_model": "meshy-6", "ultra_mode": True})

    def test_texture_alias_precedence_and_lighting_constraints(self):
        q = self.catalog.quote("image_to_3d.generate", {"image_url": IMAGE, "hd_texture": True, "texture_resolution": "8k"})
        self.assertEqual(q["credits"], 35)
        self.assert_rejected("image_to_3d.generate", {"image_url": IMAGE, "ai_model": "meshy-6-lite", "remove_lighting": False})
        self.assert_rejected("image_to_3d.generate", {"image_url": IMAGE, "model_type": "smart-topology", "image_enhancement": False})

    def test_high_resolution_refine_without_known_parent_has_blocking_unknown_price(self):
        p = {"preview_task_id": TASK, "texture_resolution": "8k"}
        q = self.catalog.quote("text_to_3d.refine", p)
        self.assertEqual(q["price_status"], "UNKNOWN")
        self.assertIsNone(q["credits"])
        self.assertFalse(q["spend_allowed"])
        q = self.catalog.quote("text_to_3d.refine", p, context={"parent": {"ai_model": "meshy-7.1"}})
        self.assertEqual(q["credits"], 15)
        self.assert_rejected("text_to_3d.refine", p, context={"parent": {"ai_model": "meshy-6-lite"}})
        q = self.catalog.quote("text_to_3d.refine", p, context={"parent": {"ai_model": "unverified-future-model"}})
        self.assertEqual(q["price_status"], "UNKNOWN")

    def test_price_freshness_uses_seven_day_utc_boundary_and_never_grants_spend(self):
        p = {"image_url": IMAGE}
        for current_day, exact in [("2026-10-17", False), ("2026-10-18", True), ("2026-10-24", True), ("2026-10-25", False), ("2027-01-01", False)]:
            with self.subTest(current_day):
                q = self.catalog.quote("image_to_3d.generate", p, as_of=current_day)
                self.assertEqual(q["source_fresh"], exact)
                self.assertEqual(q["spend_allowed"], exact)
                self.assertEqual(q["documentary_credits"], 30)
                self.assertEqual(q["price_status"], "EXACT" if exact else "UNKNOWN")
                self.assertEqual(q["authorization"], "NOT_GRANTED_BY_CATALOGUE")
                if not exact:
                    self.assertIsNone(q["credits"])
        with patch("kai_meshy.contracts.datetime") as clock:
            clock.now.return_value.date.return_value = date(2026, 10, 25)
            self.assertEqual(self.catalog.quote("image_to_3d.generate", p)["price_status"], "UNKNOWN")

    def test_retexture_rejects_ambiguous_style_and_requires_explicit_model7_multiview(self):
        p = {"model_url": MODEL, "text_style_prompt": "stone", "image_style_url": IMAGE}
        self.assert_rejected("retexture.create", p, "EXACTLY_ONE_INPUT_REQUIRED")
        p = {"model_url": MODEL, "multiview_image_urls": [IMAGE]}
        self.assert_rejected("retexture.create", p, "MULTIVIEW_EXPLICIT_MODEL_REQUIRED")
        self.assertEqual(self.catalog.quote("retexture.create", {**p, "ai_model": "meshy-7"})["credits"], 10)

    def test_resize_requires_one_positive_mode(self):
        for p in [{}, {"auto_size": False}, {"resize_height": 0}, {"resize_height": 1, "auto_size": True}, {"resize_height": 1, "resize_longest_side": 1}]:
            self.assert_rejected("resize.create", {"model_url": MODEL, **p})
        self.assertEqual(self.catalog.quote("resize.create", {"model_url": MODEL, "auto_size": True})["credits"], 1)

    def test_deprecated_remesh_shortcuts_use_dedicated_priced_operations(self):
        self.assert_rejected("remesh.create", {"model_url": MODEL, "convert_format_only": True})
        self.assert_rejected("remesh.create", {"model_url": MODEL, "resize_height": 2})

    def test_animation_exact_per_action_and_motion_price_is_unknown(self):
        for actions in [[0], list(range(10))]:
            self.assertEqual(self.catalog.quote("animation.create", {"rig_task_id": TASK, "action_ids": actions})["credits"], 3 * len(actions))
        self.assert_rejected("animation.create", {"rig_task_id": TASK, "action_id": 0, "action_ids": [1]})
        self.assert_rejected("animation.create", {"rig_task_id": TASK, "action_ids": [1, 1]})
        q = self.catalog.quote("animation.create", {"rig_task_id": TASK, "motion_task_id": TASK})
        self.assertEqual(q["price_status"], "UNKNOWN"); self.assertFalse(q["spend_allowed"])
        self.assert_rejected("animation.create", {"rig_task_id": TASK, "action_id": 0, "post_process": {"operation_type": "fbx2usdz", "fps": 30}})

    def test_text_to_motion_half_second_limits_and_price(self):
        for mode, expected in [("swift", 3), ("prime", 10)]:
            self.assertEqual(self.catalog.quote("text_to_motion.generate", {"prompt": "walk", "duration": 2.5, "mode": mode})["credits"], expected)
        for duration in [1.5, 10.5, 2.25]:
            self.assert_rejected("text_to_motion.generate", {"prompt": "walk", "duration": duration})

    def test_image_models_pose_promotion_and_aspect_constraints(self):
        for op in ["text_to_image.generate", "image_to_image.generate"]:
            for model, expected in [("nano-banana", 3), ("nano-banana-2", 6), ("nano-banana-2-lite", 3), ("nano-banana-pro", 9), ("gpt-image-2", 12 if op.startswith("image_") else 9)]:
                p = {**minimum_payload(op), "ai_model": model}
                self.assertEqual(self.catalog.quote(op, p)["credits"], expected)
            self.assert_rejected(op, {**minimum_payload(op), "generate_multi_view": True, "aspect_ratio": "1:1"})
            self.assert_rejected(op, {**minimum_payload(op), "aspect_ratio": "3:2"})
        self.assertEqual(self.catalog.quote("text_to_image.generate", {"ai_model": "nano-banana", "prompt": "figure", "pose_mode": "a-pose"})["credits"], 9)
        self.assert_rejected("text_to_image.generate", {"ai_model": "nano-banana-2-1", "prompt": "figure"})

    def test_print_is_free_only_for_analyze_but_still_a_post(self):
        self.assertEqual(self.catalog.quote("print.analyze", {"model_url": MODEL})["credits"], 0)
        self.assertFalse(self.catalog.describe("print.analyze")["paid"])
        self.assertEqual(self.catalog.describe("print.analyze")["route_methods"]["create"], "POST")
        self.assert_rejected("print.analyze", {"model_url": MODEL.replace("glb", "stl"), "intended_print_height_mm": 50})
        self.assert_rejected("print.repair", {"model_url": MODEL, "intended_print_height_mm": 50, "intended_print_longest_side_mm": 60})

    def test_split_constraints_use_known_parent_evidence(self):
        p = {"input_task_id": TASK}
        self.assert_rejected("print.auto_split", {**p, "mode": "by_parts"})
        self.assert_rejected("print.auto_split", {**p, "connector_size": .5})
        self.assert_rejected("print.auto_split", p, context={"parent": {"ai_model": "meshy-t2.5"}})
        self.assert_rejected("print.auto_split", {**p, "mode": "by_color", "prompt": "red"}, context={"parent": {"operation_id": "text_to_3d.preview"}})

    def test_creative_build_parent_candidate_and_human_gate(self):
        p = {"input_task_id": TASK, "candidate_id": "candidate-a"}
        context = {"parent": {"task_id": TASK, "operation_id": "creative_lab.keycap.prototype", "status": "SUCCEEDED", "account_verified": True, "candidate_ids": ["candidate-a"]}}
        self.assertEqual(self.catalog.quote("creative_lab.keycap.build", p, context=context)["credits"], 50)
        for change in [{"operation_id": "creative_lab.brick_figure.prototype"}, {"status": "PENDING"}, {"account_verified": False}, {"candidate_ids": ["candidate-b"]}]:
            self.assert_rejected("creative_lab.keycap.build", p, context={"parent": {**context["parent"], **change}})
        self.assertTrue(self.catalog.describe("creative_lab.brick_figure.build")["parent_constraints"]["human_visual_gate"])
        self.assert_rejected("creative_lab.brick_figure.build", {"input_task_id": TASK, "prompt": "invented"})

    def test_per_input_parent_family_is_never_generic_succeeded(self):
        self.assert_rejected("text_to_3d.refine", {"preview_task_id": TASK}, "PARENT_CAPABILITY_UNSUPPORTED", context={"parent": {"operation_id": "rigging.create", "status": "SUCCEEDED"}})
        p = {"rig_task_id": TASK, "motion_task_id": TASK}
        self.assert_rejected("animation.create", p, "PARENT_CAPABILITY_UNSUPPORTED", context={"parents": {"motion_task_id": {"operation_id": "image_to_3d.generate"}}})
        d = self.catalog.describe("animation.create")["input_fields"]
        self.assertEqual(d["rig_task_id"]["allowed_parent_capabilities"], ["rigging.create"])
        self.assertEqual(d["motion_task_id"]["allowed_parent_capabilities"], ["text_to_motion.generate"])

    def test_operation_specific_model_mime_and_format_contracts(self):
        raw = base64.b64encode(b"glTF-test-placeholder").decode()
        glb = "data:model/gltf-binary;base64," + raw
        generic = "data:application/octet-stream;base64," + raw
        self.assert_rejected("print.analyze", {"model_url": generic}, "OPERATION_MEDIA_MIME_UNSUPPORTED")
        self.assertEqual(self.catalog.quote("print.analyze", {"model_url": glb})["credits"], 0)
        self.assert_rejected("uv_unwrap.create", {"model_url": MODEL.replace(".glb", ".fbx")}, "OPERATION_MODEL_FORMAT_UNSUPPORTED")
        self.assert_rejected("convert.create", {"model_url": glb, "target_formats": ["obj"]}, "OPERATION_MEDIA_MIME_UNSUPPORTED")
        self.assertEqual(self.catalog.quote("convert.create", {"model_url": generic, "target_formats": ["obj"]})["credits"], 1)

    def test_malformed_context_is_sanitized(self):
        for row in [{"status": []}, {"ai_model": 123}, {"candidate_ids": "secret"}, {"account_verified": "yes"}]:
            message = self.assert_rejected("text_to_3d.refine", {"preview_task_id": TASK}, context={"parent": row})
            self.assertNotIn("secret", message)

    def test_multiview_texture_conflicts_include_prompt_and_disabled_texture(self):
        p = {"image_urls": [IMAGE], "texture_image_urls": [IMAGE]}
        for extra in [{"texture_prompt": "stone"}, {"texture_image_url": IMAGE}, {"should_texture": False}]:
            self.assert_rejected("multi_image_to_3d.generate", {**p, **extra}, "AMBIGUOUS_TEXTURE_REFERENCE")

    def test_keychain_unicode_normalization_and_fidget_hex(self):
        p = self.catalog.validate("creative_lab.keychain.prototype", {"image_url": IMAGE, "name_text": " \u200bABCDE\u200f "})
        self.assertEqual(p["name_text"], "ABCDE")
        self.assert_rejected("creative_lab.keychain.prototype", {"image_url": IMAGE, "name_text": "12345678901"})
        self.assert_rejected("creative_lab.fidget_pixel.build", {"input_task_id": TASK, "options": {"shape": "hex", "piece_size_mm": 10}})

    def test_fingerprint_stable_key_order_alias_and_decoded_media(self):
        raw = base64.b64encode(b"test-image-bytes").decode()
        first = {"image_url": "data:image/png;base64," + raw}
        second = {"ai_model": "latest", "image_url": "data:image/png;base64,\n" + raw[:4] + "\n" + raw[4:]}
        a = self.catalog.validation_report("image_to_3d.generate", first)
        b = self.catalog.validation_report("image_to_3d.generate", second)
        self.assertEqual(a["payload_fingerprint"], b["payload_fingerprint"])
        self.assertNotIn("base64", json.dumps(a))
        self.assertNotIn("test-image", json.dumps(a))

    def test_urls_base64_nan_and_catalogue_fail_closed(self):
        for value in ["file:///private/image.png", "https://user:password@example.test/image.png", "data:image/png;base64,***", "data:text/plain;base64,YQ==", "https://host.test/\nsecret"]:
            self.assert_rejected("image_to_3d.generate", {"image_url": value})
        self.assert_rejected("resize.create", {"model_url": MODEL, "resize_height": float("nan")})
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.json"
            target.write_text('{"schema":"bad"}')
            with self.assertRaises(ContractError):
                CapabilityCatalog(target)

    def test_bundled_contract_loads_outside_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                self.assertEqual(len(CapabilityCatalog().list()), 35)
            finally:
                os.chdir(previous)

    def test_sources_are_original_receipt_urls_not_filename_guesses(self):
        sources = self.catalog.describe("text_to_3d.preview")["sources"]
        self.assertEqual(sources["meshy-lifecycle.md"]["url"], "https://docs.meshy.ai/en/api/task-lifecycle.md")
        self.assertEqual(sources["meshy-retention.md"]["url"], "https://docs.meshy.ai/en/api/asset-retention.md")
        self.assertTrue(sources["meshy-pricing.md"]["retrieved_utc"].startswith("2026-10-18T"))


if __name__ == "__main__":
    unittest.main()
