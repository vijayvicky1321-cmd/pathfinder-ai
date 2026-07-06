import json
import os

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from system_prompt import SYSTEM_PROMPT

load_dotenv()

app = FastAPI(title="Pathfinder AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5180",
        "https://pathfinder.vijayaisec.online",
        "https://vijayvicky1321-cmd.github.io",
    ],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

JSON_INSTRUCTION = """
Respond with ONLY a single JSON object, no markdown fences, no extra text, matching this shape:
{"type": "clarify" | "answer", "text": "string", "questions": [{"question": "string", "options": ["string", ...]}]}
"questions" must be [] when type is "answer".
"""


class ChatMessage(BaseModel):
    role: str
    content: str
    type: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class Question(BaseModel):
    question: str
    options: list[str] = []


class ChatResponse(BaseModel):
    type: str
    text: str
    questions: list[Question] = []


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set on the server")

    assistant_messages = [m for m in request.messages if m.role == "assistant"]
    last_assistant = assistant_messages[-1] if assistant_messages else None
    force_answer = last_assistant is not None and last_assistant.type == "clarify"

    converted = [{"role": m.role, "content": m.content} for m in request.messages]

    if force_answer:
        converted[-1]["content"] += (
            '\n\n(GIVE ME THE FULL ANSWER NOW — Problem Summary, Roadmap, Step-by-Step '
            'Solution, and Next Steps — using best-guess assumptions for anything still '
            'unclear. Respond with "type":"answer" and "questions":[]. DO NOT ask any '
            "more questions.)"
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT + JSON_INSTRUCTION}] + converted

    def call_model(msgs):
        res = requests.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": msgs,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        res.raise_for_status()
        body = res.json()
        if "choices" not in body:
            error_info = body.get("error", body)
            raise RuntimeError(f"OpenAI error: {error_info}")
        message = body["choices"][0]["message"]
        return message.get("content") or ""

    def parse_json(raw_text):
        if not raw_text or not raw_text.strip():
            raise json.JSONDecodeError("empty response", raw_text or "", 0)
        return json.loads(raw_text)

    def parse_with_retry(msgs):
        raw_text = call_model(msgs)
        try:
            return parse_json(raw_text)
        except json.JSONDecodeError:
            retry_messages = msgs + [
                {"role": "assistant", "content": raw_text or "(empty response)"},
                {
                    "role": "system",
                    "content": (
                        "That was not valid JSON (or was empty). Re-send as a single valid "
                        'JSON object with exactly this shape: {"type": "clarify" or "answer", '
                        '"text": "your response text here", "questions": []}. No markdown '
                        "fences, no trailing commas, no stray quotes inside strings."
                    ),
                },
            ]
            raw_text = call_model(retry_messages)
            return parse_json(raw_text)

    try:
        data = parse_with_retry(messages)

        if force_answer and data.get("type") == "clarify":
            retry_messages = messages + [
                {"role": "assistant", "content": json.dumps(data)},
                {
                    "role": "user",
                    "content": (
                        'You just asked another clarifying question, which is NOT ALLOWED. '
                        'GIVE ME THE FULL ANSWER NOW — Problem Summary, Roadmap, Step-by-Step '
                        'Solution, and Next Steps — using best-guess assumptions for anything '
                        'unclear. Respond with "type":"answer" and "questions":[]. DO NOT ask '
                        "any more questions."
                    ),
                },
            ]
            data = parse_with_retry(retry_messages)

        if not data.get("text"):
            data["text"] = (
                "Sorry, I had trouble forming a full response that time. "
                "Could you try rephrasing your message?"
            )
    except Exception:
        data = {
            "type": "answer",
            "text": "Sorry, something went wrong generating a response. Please try again.",
            "questions": [],
        }

    response_type = "answer" if force_answer else data.get("type", "answer")

    return ChatResponse(
        type=response_type,
        text=data.get("text", ""),
        questions=[] if force_answer else data.get("questions", []),
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
