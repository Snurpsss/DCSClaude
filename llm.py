"""Abstraction LLM : le « cerveau » est interchangeable.

Un adaptateur expose UNE méthode :
    converse(system, tools, history, user_text, run_tool) -> (reply_text, history)
qui gère toute la boucle d'appels d'outils en interne et renvoie le texte final +
l'historique (opaque, propre à l'adaptateur) à re-passer au tour suivant.

Adaptateurs : Anthropic (Claude) et OpenAI-compatible (OpenAI, Ollama local,
Mistral, tout endpoint /v1/chat/completions). `tools` = liste au format Anthropic
(name / description / input_schema) ; convertie au vol pour OpenAI.
"""
import json
import os


class AnthropicClient:
    def __init__(self, model, max_tokens=400):
        from anthropic import Anthropic
        self._c = Anthropic()          # lit ANTHROPIC_API_KEY
        self.model = model
        self.max_tokens = max_tokens

    def converse(self, system, tools, history, user_text, run_tool):
        messages = list(history)
        messages.append({"role": "user", "content": user_text})
        while True:
            resp = self._c.messages.create(
                model=self.model, max_tokens=self.max_tokens,
                system=system, tools=tools, messages=messages)
            messages.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "tool_use":
                results = []
                for b in resp.content:
                    if b.type == "tool_use":
                        r = run_tool(b.name, b.input)
                        results.append({"type": "tool_result", "tool_use_id": b.id,
                                        "content": json.dumps(r, ensure_ascii=False)})
                messages.append({"role": "user", "content": results})
                continue
            text = "".join(b.text for b in resp.content if b.type == "text")
            return text, messages


class OpenAICompatClient:
    """OpenAI, Ollama (local), Mistral… — tout endpoint /v1/chat/completions."""
    def __init__(self, model, base_url, api_key="", max_tokens=400):
        self.model = model
        self.base = base_url.rstrip("/")
        self.key = api_key
        self.max_tokens = max_tokens

    @staticmethod
    def _tools(tools):
        return [{"type": "function", "function": {
            "name": t["name"], "description": t.get("description", ""),
            "parameters": t.get("input_schema", {"type": "object", "properties": {}})}}
            for t in tools]

    def converse(self, system, tools, history, user_text, run_tool):
        import httpx
        convo = list(history)                      # historique SANS le message system
        convo.append({"role": "user", "content": user_text})
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        otools = self._tools(tools)
        while True:
            msgs = [{"role": "system", "content": system}] + convo
            payload = {"model": self.model, "messages": msgs,
                       "tools": otools, "max_tokens": self.max_tokens}
            r = httpx.post(self.base + "/chat/completions", json=payload,
                           headers=headers, timeout=90)
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            convo.append(msg)
            tcs = msg.get("tool_calls")
            if tcs:
                for tc in tcs:
                    fn = tc.get("function", {})
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    res = run_tool(fn.get("name", ""), args)
                    convo.append({"role": "tool", "tool_call_id": tc.get("id"),
                                  "content": json.dumps(res, ensure_ascii=False)})
                continue
            return (msg.get("content") or ""), convo


def client_key(cfg):
    """Identité du client (pour détecter un changement de fournisseur/modèle)."""
    return (cfg.get("llm_provider", "anthropic"),
            cfg.get("llm_model", ""), cfg.get("llm_base_url", ""),
            cfg.get("claude_model", ""))


def make_client(cfg):
    prov = cfg.get("llm_provider", "anthropic")
    if prov == "anthropic":
        model = cfg.get("llm_model") or cfg.get("claude_model") or "claude-sonnet-4-6"
        return AnthropicClient(model)
    if prov == "ollama":
        base = cfg.get("llm_base_url") or "http://localhost:11434/v1"
        model = cfg.get("llm_model") or "llama3.1"
        return OpenAICompatClient(model, base, "")
    # openai (ou tout endpoint compatible)
    base = cfg.get("llm_base_url") or "https://api.openai.com/v1"
    model = cfg.get("llm_model") or "gpt-4o-mini"
    key = os.environ.get(cfg.get("llm_api_key_env") or "OPENAI_API_KEY", "")
    return OpenAICompatClient(model, base, key)
