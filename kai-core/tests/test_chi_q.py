from kai_core.models.chi_q import ChiQState, calculate_chi_q, decision_hint


def test_chi_q_range_and_decision():
    state = ChiQState(0.8, 0.2, 0.7, 0.3, 0.9, 0.2, 0.7)
    score = calculate_chi_q(state)
    assert 0 <= score <= 1
    assert decision_hint(state) in {
        "detener_edicion_y_pedir_aprobacion",
        "priorizar_memoria_y_cola",
        "continuar_con_precaucion",
        "avanzar",
    }
