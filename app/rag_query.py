import requests
from app.config import OPENROUTER_API_KEY
from app.vector_search import VectorSearch

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4-flash-0731"
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}
TOP_K = 5


class RagQuery:
    def __init__(self):
        self.search = VectorSearch()

    def ask(self, question):
        results = self.search.search(question, top_k=TOP_K)

        context = "\n\n---\n\n".join(r["text"] for r in results)

        prompt = (
            "Você é um assistente especialista em Chrono Trigger. "
            "Responda a pergunta do usuário em português brasileiro, "
            "usando apenas as informações do contexto abaixo, mesmo que "
            "o contexto esteja em inglês. Se o contexto não tiver a "
            "resposta, diga que não sabe.\n\n"
            f"Contexto:\n{context}\n\n"
            f"Pergunta: {question}"
        )

        answer = self._generate(prompt)

        return answer, results

    def _generate(self, prompt):
        response = requests.post(
            url=OPENROUTER_URL,
            headers=HEADERS,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    rag = RagQuery()

    question = input("Qual a pergunta? ")
    answer, sources = rag.ask(question)

    print("Resposta:")
    print(answer)
    print()
    print("Fontes usadas:")
    for r in sources:
        print(f" - {r['chunk_id']} (similaridade {r['similarity']:.4f})")
