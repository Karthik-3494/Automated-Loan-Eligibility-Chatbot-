import argparse
import json
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agent_state import AgentState
from request_id_generator import new_request_id
from sequential_nodes import kyc_node, ocr_node, policy_node, receive_node, synthesis_node, validation_node


def build_sequential_agent():
    graph = StateGraph(AgentState)
    graph.add_node("receive", receive_node)
    graph.add_node("ocr", ocr_node)
    graph.add_node("validate", validation_node)
    graph.add_node("kyc", kyc_node)
    graph.add_node("policy", policy_node)
    graph.add_node("synthesis", synthesis_node)

    graph.add_edge(START, "receive")
    graph.add_edge("receive", "ocr")
    graph.add_edge("ocr", "validate")
    graph.add_edge("validate", "kyc")
    graph.add_edge("kyc", "policy")
    graph.add_edge("policy", "synthesis")
    graph.add_edge("synthesis", END)
    return graph.compile()


sequential_agent = build_sequential_agent()


def run_sequential_agent(input_path):
    source = Path(input_path)
    if source.is_file():
        files = [source]
    elif source.is_dir():
        files = sorted(
            path for path in source.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"}
        )
    else:
        raise FileNotFoundError(f"Input path does not exist: {source}")

    Path("logs").mkdir(exist_ok=True)
    return [
        sequential_agent.invoke({"document_path": str(path), "request_id": new_request_id()})
        for path in files
    ]


def main():
    parser = argparse.ArgumentParser(description="Run the fixed sequential document workflow")
    parser.add_argument("input_path", help="An image or PDF file or a folder containing them")
    args = parser.parse_args()
    print(json.dumps(run_sequential_agent(args.input_path), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
