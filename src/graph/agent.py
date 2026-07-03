from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes import (
    plan,
    write_code,
    execute,
    inspect,
    clarify,
    narrate,
    finalize,
    handle_error,
)
from graph.edges import route_after_inspect


def _build_graph():
    g = StateGraph(AgentState)

    g.add_node("plan", plan)
    g.add_node("write_code", write_code)
    g.add_node("execute", execute)
    g.add_node("inspect", inspect)
    g.add_node("clarify", clarify)
    g.add_node("narrate", narrate)
    g.add_node("finalize", finalize)
    g.add_node("handle_error", handle_error)

    g.set_entry_point("plan")

    g.add_conditional_edges(
        "plan",
        lambda s: "handle_error" if s.get("error") else "write_code",
        {"handle_error": "handle_error", "write_code": "write_code"},
    )
    g.add_conditional_edges(
        "write_code",
        lambda s: "handle_error" if s.get("error") else "execute",
        {"handle_error": "handle_error", "execute": "execute"},
    )
    g.add_edge("execute", "inspect")
    g.add_conditional_edges(
        "inspect",
        route_after_inspect,
        {
            "handle_error": "handle_error",
            "narrate": "narrate",
            "clarify": "clarify",
            "write_code": "write_code",
        },
    )

    g.add_edge("clarify", END)
    g.add_edge("narrate", "finalize")
    g.add_edge("finalize", END)
    g.add_edge("handle_error", END)

    return g.compile()


agentic_ai = _build_graph()
