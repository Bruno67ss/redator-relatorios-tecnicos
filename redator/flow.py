"""Estado transitório do formulário; nenhum dado é persistido aqui."""
from .demo import demo_case
from .domain import Identity
from .labels import equipment_names


def invalidate(state):
    for key in ("proposal", "proposal_source", "report_case", "draft", "review_text", "exports", "source_fingerprint", "details_dirty", "details_resolved", "organization_approved", "report_notes"):
        state.pop(key, None)
    state["approved"] = False


def add_equipment(state):
    number = state.get("next_equipment", 2)
    alias = f"E{number}"
    state["equipment_ids"] = list(state["equipment_ids"]) + [alias]
    state["next_equipment"] = number + 1
    state[f"kind_{alias}"] = "Módulo eletrônico"
    state[f"side_{alias}"] = ""
    invalidate(state)


def remove_equipment(state, alias):
    if len(state["equipment_ids"]) <= 1:
        return
    state["equipment_ids"] = [item for item in state["equipment_ids"] if item != alias]
    for key in list(state):
        if key.endswith("_" + alias) or key.startswith("voice_" + alias + "_"):
            state.pop(key, None)
    invalidate(state)


def example_assessment(item):
    return (f"Observações: {item.observations}\n\nProcedimentos realizados: {item.procedures}"
            f"\n\nResultado e limitações: {item.result}\n\nConclusão: {item.conclusion}")


def load_example(state):
    state.clear()
    sample = demo_case()
    state["ui_version"] = 4
    state["equipment_ids"] = [i.alias for i in sample.identities]
    state["next_equipment"] = len(sample.identities) + 1
    state["requester"], state["department"] = sample.requester, sample.department
    state["city"], state["responsible"] = sample.city, sample.responsible
    for identity, technical in zip(sample.identities, sample.technical):
        for name in ("kind", "side", "model", "serial"):
            value = getattr(identity, name)
            state[f"{name}_{identity.alias}"] = "" if name == "side" and value not in ("Direito", "Esquerdo") else value
    names = equipment_names(sample.identities)
    state["general_assessment"] = "\n\n".join(
        f"Quanto ao {names[t.alias]}, {t.observations} {t.procedures} {t.result} {t.conclusion}"
        for t in sample.technical)


def initialize(state):
    if state.get("ui_version") == 3:
        # Preserva inclusive os trechos digitados à mão da interface anterior.
        ids = list(state.get("equipment_ids", ["E1"]))
        identities = tuple(Identity(alias, state.get(f"kind_{alias}", "Módulo eletrônico"),
                                   state.get(f"side_{alias}", ""), "", "") for alias in ids)
        names = equipment_names(identities)
        previous = state.get("general_assessment", "").strip()
        parts = [previous] if previous else []
        for alias in ids:
            text = state.get(f"assessment_{alias}", "").strip()
            if text and text not in previous:
                parts.append(f"Quanto ao {names[alias]}, {text}")
        state["general_assessment"] = "\n\n".join(parts)
        state["ui_version"] = 4
        invalidate(state)
    elif state.get("ui_version") != 4:
        state.clear()
        state["ui_version"] = 4
        state["equipment_ids"] = ["E1"]
        state["next_equipment"] = 2


def clear_case(state):
    state.clear()
    initialize(state)
