from projects.ultratrain.peft_policy import PeftStatus, evaluate_peft_profile


def test_peft_021_does_not_clear_open_trainable_tokens_bias_gate():
    result = evaluate_peft_profile({
        "peft": {
            "version": "0.21.0",
            "trainable_tokens": True,
            "output_head_has_bias": True,
        }
    })
    assert result.status is PeftStatus.NEEDS_CANARY
    assert "peft_adapter_init_logits_equal" in result.canaries


def test_riemannian_lora_requires_peft_021_or_newer():
    result = evaluate_peft_profile({
        "peft": {"version": "0.20.0", "method": "lora", "optimizer": "riemannian_lora"}
    })
    assert result.status is PeftStatus.UNSUPPORTED
    assert "peft.riemannian_lora.requires_021" in result.rules


def test_riemannian_lora_is_explicit_capability_not_auto_default():
    result = evaluate_peft_profile({
        "peft": {"version": "0.21.0", "method": "lora", "optimizer": "riemannian_lora"}
    })
    assert result.status is PeftStatus.SUPPORTED
    assert "peft.riemannian_lora.explicit" in result.decisions


def test_riemannian_lora_rejected_for_non_lora_method():
    result = evaluate_peft_profile({
        "peft": {"version": "0.21.0", "method": "osf", "optimizer": "riemannian_lora"}
    })
    assert result.status is PeftStatus.UNSUPPORTED
    assert "peft.riemannian_lora.requires_lora" in result.rules


def test_multi_adapter_target_parameters_requires_peft_021():
    result = evaluate_peft_profile({
        "peft": {
            "version": "0.20.0",
            "method": "lora",
            "target_parameters": True,
            "adapter_count": 2,
        }
    })
    assert result.status is PeftStatus.UNSUPPORTED
    assert "peft.target_parameters.multi_adapter.requires_021" in result.rules


def test_peft_021_multi_adapter_target_parameters_is_supported():
    result = evaluate_peft_profile({
        "peft": {
            "version": "0.21.0",
            "method": "lora",
            "target_parameters": True,
            "adapter_count": 2,
        }
    })
    assert result.status is PeftStatus.SUPPORTED
    assert "peft.target_parameters.multi_adapter_021" in result.decisions
