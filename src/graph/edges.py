from config.settings import get_settings
from graph.state import AgentState


def route_after_inspect(state: AgentState) -> str:
    """Route after the inspect node per the agent-graph topology."""
    if state.get("error"):
        return "handle_error"

    inspection = state.get("inspection") or {}
    if inspection.get("ok"):
        return "narrate"
    if inspection.get("needs_clarification"):
        return "clarify"

    max_attempts = get_settings().max_attempts
    if state.get("attempts", 0) < max_attempts:
        return "write_code"  # retry with a different approach
    return "narrate"  # exhausted retries -> narrate best-effort / report failure
