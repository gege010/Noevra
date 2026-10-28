"""Small async adapters for officially supported OAuth model inference."""
from __future__ import annotations
import json
from urllib.parse import quote
import httpx
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class OAuthChatModel(BaseChatModel):
    provider: str
    model: str
    token: str = Field(repr=False, exclude=True)
    project: str = ""

    @property
    def _llm_type(self):
        return "official-oauth"

    @property
    def _identifying_params(self):
        return {"provider": self.provider, "model": self.model}

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("This adapter supports async inference only.")

    async def _agenerate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15), follow_redirects=False) as client:
            if self.provider == "openai":
                payload = {"model": self.model, "store": False, "stream": True,
                           "input": [{"role": "developer" if m.type == "system" else "assistant" if m.type == "ai" else "user", "content": str(m.content)} for m in messages]}
                complete, text = False, []
                async with client.stream("POST", "https://api.openai.com/v1/responses", headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        raise RuntimeError("ChatGPT inference failed. Reconnect or check your account limits.")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            continue
                        event = json.loads(data)
                        kind = event.get("type")
                        if kind == "response.output_text.delta":
                            text.append(event.get("delta", ""))
                        elif kind == "response.completed":
                            complete = True
                        elif kind in ("response.failed", "response.incomplete", "error"):
                            raise RuntimeError("ChatGPT did not complete this response. Check plan access and usage limits.")
                if not complete:
                    raise RuntimeError("ChatGPT response stream ended before completion.")
                content = "".join(text)
            else:
                headers["x-goog-user-project"] = self.project
                system = "\n".join(str(m.content) for m in messages if m.type == "system")
                payload = {"contents": [{"role": "model" if m.type == "ai" else "user", "parts": [{"text": str(m.content)}]} for m in messages if m.type != "system"]}
                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}
                response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent", headers=headers, json=payload)
                if response.status_code != 200:
                    raise RuntimeError("Gemini inference failed. Reconnect or check the Cloud project's API and billing permissions.")
                result = response.json()
                candidates = result.get("candidates", [])
                if not candidates or candidates[0].get("finishReason") not in (None, "STOP"):
                    raise RuntimeError("Gemini did not complete this response.")
                content = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []))
        if not content.strip():
            raise RuntimeError("The provider returned no research content.")
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
