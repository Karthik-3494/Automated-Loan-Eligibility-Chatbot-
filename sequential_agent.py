from pathlib import Path
from langgraph.graph import StateGraph, START, END
from agent_state import AgentState
from request_id_generator import new_request_id
from sequential_nodes import (
    receive_node,
    knockout_node,
    financial_node,
    kyc_node,
    eligibility_node,
    policy_node,
    report_node,
)


def build_sequential_agent():
    graph = StateGraph(AgentState)
    for name, node in [
        ("receive", receive_node),
        ("knockout", knockout_node),
        ("financial", financial_node),
        ("kyc", kyc_node),
        ("eligibility", eligibility_node),
        ("policy", policy_node),
        ("report", report_node),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "receive")
    graph.add_edge("receive", "knockout")
    graph.add_edge("knockout", "financial")
    graph.add_edge("financial", "kyc")
    graph.add_edge("kyc", "eligibility")
    graph.add_edge("eligibility", "policy")
    graph.add_edge("policy", "report")
    graph.add_edge("report", END)
    return graph.compile()


sequential_agent = build_sequential_agent()


def run_application(applicant):
    state = {
        "request_id": applicant.get("request_id")
        or new_request_id(Path(__file__).resolve().parent / "logs"),
        **applicant,
    }
    return sequential_agent.invoke(state)
