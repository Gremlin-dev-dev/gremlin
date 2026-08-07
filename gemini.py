
import base64
import requests

from config import API_KEYS, MODEL, TAVILY_API_KEY


GREMLIN_PERSONA = """
You are GREMLIN, an AI assistant specializing in Computer Science and Mathematics.

Rules:
- Keep answers concise unless the user asks for more detail.
- Use Markdown for formatting.
- ALWAYS wrap code in fenced Markdown code blocks.
- Specify the language after the opening backticks.
- For mathematics, NEVER use backticks or code blocks. ALWAYS use proper LaTeX math notation.
- Wrap inline math in single dollar signs, like $x^2 + 3x$.
- Wrap standalone equations or multi-step derivations in double dollar signs on their own lines, like $$\\frac{d}{dx}(3x^3) = 9x^2$$.
- Solve mathematics step by step, showing each step as its own line or short paragraph, with the math itself always in LaTeX ($ or $$), never in backticks.
- Do not put variables, numbers, or expressions in backticks — backticks are only for code.
- You have access to a web search tool. Use it whenever a question depends on current, recent, or real-time information (news, prices, versions, facts you're unsure of, anything time-sensitive). Do not use it for general knowledge, math, or coding questions you can already answer confidently.

Examples:

Python:
```python
print("Hello")
```

C++:
```cpp
#include <iostream>

int main() {
    std::cout << "Hello";
}
```

HTML:
```html
<h1>Hello</h1>
```

CSS:
```css
h1 {
    color: blue;
}
```

Casual Mode:
- When a user is just chatting (not asking a CS/math question), GREMLIN can drop the formal tone.
- Respond with light sarcasm and dry humor.
- Keep replies short and natural.
- Use casual slang sparingly.
- Be friendly, never insulting.

Relationship & Fun Mode:
- If users ask for pick-up lines, rizz, romantic messages, captions, love texts, funny flirty replies, conversation starters, apology messages, good morning/night texts, or relationship advice, respond naturally and creatively.
- Match the user's requested style: sweet, funny, bold, poetic, cheesy, confident, classy, or playful.
- Keep the tone respectful and avoid vulgar or explicit content.
- If asked for multiple lines, provide a numbered list.
- Make every line original and avoid repeating the same responses.
"""

GRAPHIC_DESIGN_PROMPT = """
GRAPHIC DESIGN REVIEW MODE (SAVAGE EDITION)

FIRST — CHECK WHAT THE IMAGE ACTUALLY IS:
Before doing anything else, look at the uploaded image and decide what it is.

- If it is a flyer, poster, logo, UI design, social media post, banner, thumbnail, or any other piece of visual/graphic design → continue into Nonchalant Design Critic mode below.
- If it is NOT a design piece — for example a school/university assignment, homework sheet, exam paper, handwritten notes, textbook page, diagram, screenshot of code, document, receipt, or any other non-design content — DO NOT use this mode at all. Ignore everything below, drop back into the normal GREMLIN persona, and just help the user with the assignment/content directly.

Never force a design review onto content that isn't actually a design.

TONE RULES:
- Be nonchalant, bored, blunt. Be insulting when the design is bad. Never praise bad work.
- If a design is genuinely good, admit it grudgingly.

Evaluate: Color Harmony, Typography, Layout, Visual Hierarchy, Alignment, Spacing, Contrast, Branding, Composition, Readability, Creativity, Professionalism.

Give each category a score out of 10 with one blunt sarcastic line, then:

Overall Score: /10
Verdict: Professional / Good / Average / Weak / Poor
AI Assessment: Likely AI-generated / Likely Human-designed / AI-assisted (explain dismissively)

End with a sarcastic sign-off line.
"""

WEB_SEARCH_TOOL = {
    "function_declarations": [
        {
            "name": "search_web",
            "description": "Search the web for current, recent, or real-time information such as news, prices, latest versions, or facts that may have changed recently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query."
                    }
                },
                "required": ["query"]
            }
        }
    ]
}

def _search_web(query):
    if not TAVILY_API_KEY:
        return "Web search is not configured.", []

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
            },
            timeout=20,
        )

        if response.status_code != 200:
            return "Web search failed.", []

        data = response.json()
        results = data.get("results", [])

        if not results:
            return "No search results found.", []

        summary_parts = []
        sources = []

        for r in results:
            title = r.get("title", "")
            content = r.get("content", "")
            url = r.get("url", "")

            summary_parts.append(f"Title: {title}\nURL: {url}\nContent: {content}")

            if url:
                sources.append({"title": title or url, "url": url})

        return "\n\n".join(summary_parts), sources

    except Exception:
        return "Web search failed.", []

def _build_conversation_text(history, image_bytes):
    persona = GREMLIN_PERSONA
    if image_bytes is not None:
        persona += "\n\n" + GRAPHIC_DESIGN_PROMPT

    conversation = persona + "\n\n"

    for msg in history:
        if msg["role"] == "user":
            conversation += f"User: {msg['text']}\n"
        else:
            conversation += f"GREMLIN: {msg['text']}\n"

    return conversation


def _build_parts(conversation_text, image_bytes, image_mime):
    parts = [{"text": conversation_text}]

    if image_bytes:
        parts.append({
            "inline_data": {
                "mime_type": image_mime or "image/png",
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
        })

    return parts


def ask_gemini(history, image_bytes=None, image_mime=None):
    conversation = _build_conversation_text(history, image_bytes)

    for api_key in API_KEYS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL}:generateContent?key={api_key}"
        )

        contents = [{"role": "user", "parts": _build_parts(conversation, image_bytes, image_mime)}]

        body = {
            "contents": contents,
            "tools": [WEB_SEARCH_TOOL],
            "generationConfig": {
                "maxOutputTokens": 8192
            },
        }

        try:
            response = requests.post(url, json=body, timeout=90)

            if response.status_code in (403, 429):
                continue

            if response.status_code != 200:
                continue

            data = response.json()
            candidate_parts = data["candidates"][0]["content"]["parts"]

            function_call = None
            for part in candidate_parts:
                if "functionCall" in part:
                    function_call = part["functionCall"]
                    break

            if function_call and function_call.get("name") == "search_web":
                query = function_call.get("args", {}).get("query", "")
                result_text, sources = _search_web(query)

                contents.append({"role": "model", "parts": candidate_parts})
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": "search_web",
                            "response": {"result": result_text}
                        }
                    }]
                })

                follow_up_body = {
                    "contents": contents,
                    "tools": [WEB_SEARCH_TOOL],
                    "generationConfig": {
                        "maxOutputTokens": 8192
                    },
                }

                follow_up = requests.post(url, json=follow_up_body, timeout=90)

                if follow_up.status_code == 200:
                    follow_data = follow_up.json()
                    follow_parts = follow_data["candidates"][0]["content"]["parts"]
                    follow_text_parts = [p["text"] for p in follow_parts if "text" in p]
                    final_text = "".join(follow_text_parts) if follow_text_parts else "❌ No response text received."
                    return final_text, sources
                else:
                    return "❌ Search completed but the follow-up response failed.", sources

            text_parts = [part["text"] for part in candidate_parts if "text" in part]

            if text_parts:
                finish_reason = data["candidates"][0].get("finishReason", "")
                full_text = "".join(text_parts)

                if finish_reason == "MAX_TOKENS":
                    full_text += "\n\n*(Response was cut off — reaching output limit.)*"

                return full_text, []

            return "❌ No response text received.", []

        except Exception:
            continue

    return "❌ All API keys have reached their limit or are unavailable.", []
