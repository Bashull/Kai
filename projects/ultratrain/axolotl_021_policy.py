"""UltraTrain Axolotl 0.21.0 correctness gate. STAGING, not deployed.
Source: https://github.com/axolotl-ai-cloud/axolotl/releases/tag/v0.21.0
Caller-provided versions and flags are NOT independent evidence.
"""
from __future__ import annotations
import re

def _v(x):
    m = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", x) if isinstance(x, str) else None
    return tuple(int(y or 0) for y in m.groups()) if m else None

def axolotl_021_findings(profile):
    if not isinstance(profile, dict):
        return [{"status":"NEEDS_CANARY","rule":"axolotl.profile_shape"}]
    for k in ("packages","axolotl","runtime","distributed","training"):
        if k in profile and not isinstance(profile[k],dict):
            return [{"status":"NEEDS_CANARY","rule":"axolotl.profile_shape"}]
    pk=profile.get("packages") or {}
    ax=profile.get("axolotl") or {}
    rt=profile.get("runtime") or {}
    ds=profile.get("distributed") or {}
    if not (pk.get("axolotl") or ax or (profile.get("training") or {}).get("engine")=="axolotl"):
        return []
    out=[]
    def add(status,rule,canary=""):
        out.append({"status":status,"rule":rule,"canary":canary})
    ver=_v(pk.get("axolotl") or ax.get("version"))
    if ver is None:
        add("NEEDS_CANARY","axolotl.version_identity","package_probe")
        return out
    if ver < (0,20,0):
        return out
    py=_v(rt.get("python_version"))
    torch=_v(pk.get("torch"))
    if py is None: add("NEEDS_CANARY","axolotl.python_identity","python_probe")
    elif py < (3,12,0): add("UNSUPPORTED","axolotl.python_min_312")
    if torch is None: add("NEEDS_CANARY","axolotl.torch_identity","torch_probe")
    elif torch < (2,13,0): add("UNSUPPORTED","axolotl.torch_min_213")
    elif ver >= (0,21,0) and torch >= (2,15,0): add("UNSUPPORTED","axolotl.torch_lt_215")
    if ds.get("fsdp_version")==1: add("UNSUPPORTED","axolotl.fsdp1_removed")
    ep=ax.get("expert_parallelism") is True or ds.get("expert_parallelism") is True
    risks=(
      (ep and ax.get("sonicmoe") is True and ax.get("nvfp4") is True and ax.get("expert_lora") is True,"sonicmoe_nvfp4_expert_lora","expert_weight_delta"),
      (ep and ds.get("resume_checkpoint") is True,"ep_resume_state","ep_roundtrip"),
      (ds.get("fsdp_version")==2 and ax.get("activation_checkpointing") is True and ax.get("lora_adapter_save") is True,"fsdp2_lora_empty","adapter_roundtrip"))
    for enabled,name,canary in risks:
        if enabled:
            if ver < (0,21,0): add("UNSUPPORTED","axolotl.pre021."+name)
            else: add("NEEDS_CANARY","axolotl.021."+name+"_verify",canary)
    if ax.get("diffusion_lm") is True or ax.get("multimodal_preference") is True:
        if ver < (0,21,0): add("UNSUPPORTED","axolotl.021.new_recipe_requires_021")
        else: add("NEEDS_CANARY","axolotl.021.new_recipe_canary","loss_schema_parity")
    if ver >= (0,21,0):
        if ax.get("legacy_diffusion_config") is True: add("NEEDS_CANARY","axolotl.021.diffusion_key_deprecated","migrate_yaml")
        if ax.get("upgrading_from") and (ax.get("packed_sequences") or ax.get("gradient_checkpointing")):
            add("NEEDS_CANARY","axolotl.021.changed_defaults","packing_grad_ab")
        if ax.get("vllm_serve") is True:
            vv=_v(pk.get("vllm") or rt.get("vllm_version"))
            if vv is None: add("NEEDS_CANARY","axolotl.021.vllm_identity","vllm_probe")
            elif vv < (0,30,0): add("UNSUPPORTED","axolotl.021.vllm_min_030")
            else: add("NEEDS_CANARY","axolotl.021.vllm_e2e","serve_canary")
    return out

def assess_axolotl_021(profile):
    issues=axolotl_021_findings(profile)
    return max(issues,key=lambda x: 2 if x["status"]=="UNSUPPORTED" else 1) if issues else None
