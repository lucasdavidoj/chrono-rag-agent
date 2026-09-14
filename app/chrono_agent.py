import json
import logging
from typing import TypedDict

import requests
from app.config import OPENROUTER_API_KEY
from app.rag_query import RagQuery
from langgraph.graph import END, StateGraph

logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s"
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4-flash-0731"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}
TOP_K = 5


class AgentState(TypedDict):
    question: str
    answer: str
    sources: list
    is_on_topic: bool


class RouterResponse(TypedDict):
    is_on_topic: bool


class ChronoAgent:
    def __init__(self):
        self.rag_query = RagQuery()

    def router_node(self, state: AgentState) -> dict:
        prompt = (
            "Você é um assistente roteador. "
            "Decida se a pergunta do usuário está relacionada a Chrono Trigger. "
            "Responda em JSON, exatamente neste formato: \n"
            '{"is_on_topic": true} ou {"is_on_topic": false}\n\n'
            f"Pergunta: {state['question']}"
        )

        raw_response = self._generate(prompt, json_mode=True)

        try:
            parsed = json.loads(raw_response)
            is_on_topic = bool(parsed["is_on_topic"])
        except (json.JSONDecodeError, KeyError) as e:
            is_on_topic = True

            logging.warning(f"[router_node] Pergunta: {state['question']} -> {e}")

        return {"is_on_topic": is_on_topic}

    def _generate(self, prompt, json_mode=False):
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(url=OPENROUTER_URL, headers=HEADERS, json=payload)
        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]

    def route(self, state: AgentState) -> str:
        if state["is_on_topic"]:
            return "rag"

        return "decline"

    def rag_node(self, state: AgentState) -> dict:
        answer, sources = self.rag_query.ask(state["question"])

        return {"answer": answer, "sources": sources}

    def decline_node(self, state: AgentState) -> dict:
        return {
            "answer": "Só sei responder perguntas sobre Chrono Trigger.",
            "sources": [],
        }

    def build(self):
        graph = StateGraph(AgentState)

        graph.add_node("router", self.router_node)
        graph.add_node("rag", self.rag_node)
        graph.add_node("decline", self.decline_node)

        graph.set_entry_point("router")

        graph.add_conditional_edges(
            "router",
            self.route,
            {
                "rag": "rag",
                "decline": "decline",
            },
        )

        graph.add_edge("rag", END)
        graph.add_edge("decline", END)

        return graph.compile()


if __name__ == "__main__":
    agent = ChronoAgent().build()

    while True:
        question = input("Qual a pergunta? ")

        if question.strip().lower() == "sair":
            break

        result = agent.invoke(
            {"question": question, "answer": "", "sources": [], "is_on_topic": False}
        )

        print()
        print("Resposta:")
        print(result["answer"])

        if result["sources"]:
            print()
            print("Fontes usadas:")
            for r in result["sources"]:
                print(f" - {r['chunk_id']} (similaridade {r['similarity']:.4f})")

        print()
