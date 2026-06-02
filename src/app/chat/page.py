"""HTML page for the thin internal chat UI."""

from __future__ import annotations


def render_internal_chat_page(*, api_v1_prefix: str) -> str:
    """Return the minimal internal chat page."""

    api_endpoint = f"{api_v1_prefix.rstrip('/')}/chat/posts"
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Posts Chat</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f5efe3;
        --panel: rgba(255, 252, 245, 0.92);
        --ink: #192126;
        --muted: #5d6a72;
        --line: rgba(25, 33, 38, 0.12);
        --accent: #0f766e;
        --accent-soft: rgba(15, 118, 110, 0.12);
        --warning: #9a3412;
        --warning-soft: rgba(154, 52, 18, 0.12);
        --empty: #475569;
        --empty-soft: rgba(71, 85, 105, 0.12);
        --shadow: 0 24px 50px rgba(25, 33, 38, 0.12);
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top, rgba(15, 118, 110, 0.18), transparent 34%),
          linear-gradient(160deg, #f8f4eb 0%, var(--bg) 58%, #efe4cf 100%);
      }}

      main {{
        width: min(860px, calc(100vw - 32px));
        margin: 48px auto;
        padding: 28px;
        border: 1px solid var(--line);
        border-radius: 28px;
        background: var(--panel);
        box-shadow: var(--shadow);
        backdrop-filter: blur(16px);
      }}

      h1 {{
        margin: 0;
        font-size: clamp(2rem, 4vw, 3rem);
        line-height: 1;
      }}

      .lede {{
        margin: 12px 0 0;
        color: var(--muted);
        max-width: 48rem;
      }}

      .stack {{
        display: grid;
        gap: 16px;
        margin-top: 28px;
      }}

      .composer {{
        display: grid;
        gap: 12px;
      }}

      textarea {{
        width: 100%;
        min-height: 96px;
        padding: 16px 18px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.78);
        color: var(--ink);
        font: inherit;
        resize: vertical;
      }}

      button {{
        justify-self: start;
        border: 0;
        border-radius: 999px;
        padding: 12px 20px;
        color: white;
        background: linear-gradient(135deg, #0f766e, #115e59);
        font: inherit;
        cursor: pointer;
      }}

      button[disabled] {{
        cursor: wait;
        opacity: 0.7;
      }}

      .messages {{
        display: grid;
        gap: 12px;
      }}

      .message {{
        padding: 16px 18px;
        border-radius: 20px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.74);
      }}

      .message.user {{
        margin-left: auto;
        max-width: 80%;
        background: rgba(15, 118, 110, 0.1);
      }}

      .message.assistant.empty {{
        background: rgba(255, 255, 255, 0.86);
        border-style: dashed;
      }}

      .message.assistant.no_posts {{
        background: var(--empty-soft);
      }}

      .message.assistant.insufficient_evidence {{
        background: var(--warning-soft);
      }}

      .message.assistant.error {{
        background: rgba(127, 29, 29, 0.12);
      }}

      .eyebrow {{
        display: inline-block;
        margin-bottom: 8px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}

      .assistant.answered .eyebrow {{
        color: var(--accent);
      }}

      .assistant.no_posts .eyebrow {{
        color: var(--empty);
      }}

      .assistant.insufficient_evidence .eyebrow {{
        color: var(--warning);
      }}

      .assistant.error .eyebrow {{
        color: #7f1d1d;
      }}

      .citations {{
        margin: 14px 0 0;
        padding: 0 0 0 18px;
      }}

      .citations li + li {{
        margin-top: 10px;
      }}

      .citations a {{
        color: inherit;
      }}

      .muted {{
        color: var(--muted);
      }}

      .status {{
        min-height: 1.25rem;
        color: var(--muted);
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Ask About Your Posts</h1>
      <p class="lede">
        Thin internal client for the posts Q&amp;A API. It reuses current browser credentials
        when present, shows grounded citations, and keeps the latest <code>session_id</code>
        for follow-up turns in the same conversation.
      </p>

      <section class="stack">
        <form id="chat-form" class="composer">
          <label for="chat-input">Question</label>
          <textarea
            id="chat-input"
            name="question"
            placeholder="What themes show up in my recent posts?"
            required
          ></textarea>
          <button id="chat-submit" type="submit">Ask</button>
          <p id="chat-status" class="status" aria-live="polite"></p>
        </form>

        <section
          id="chat-messages"
          class="messages"
          aria-live="polite"
          aria-label="Conversation"
        >
          <article id="empty-state" class="message assistant empty">
            <span class="eyebrow">Start Here</span>
            <p>
              Ask a question about your posts to start the conversation. This initial empty
              state is separate from the later "no posts yet" and "not enough information"
              fallback responses.
            </p>
          </article>
        </section>
      </section>
    </main>

    <script>
      const apiEndpoint = {api_endpoint!r};
      const form = document.getElementById("chat-form");
      const input = document.getElementById("chat-input");
      const submitButton = document.getElementById("chat-submit");
      const messages = document.getElementById("chat-messages");
      const status = document.getElementById("chat-status");
      let activeSessionId = null;

      const stateLabels = {{
        answered: "Grounded answer",
        no_posts: "No posts yet",
        insufficient_evidence: "Not enough information",
        error: "Upstream error",
      }};

      function appendMessage(role, content, state) {{
        const article = document.createElement("article");
        article.className = `message ${{role}}${{state ? ` ${{state}}` : ""}}`;

        if (role === "assistant" && state) {{
          const eyebrow = document.createElement("span");
          eyebrow.className = "eyebrow";
          eyebrow.textContent = stateLabels[state] || "Assistant";
          article.appendChild(eyebrow);
        }}

        const paragraph = document.createElement("p");
        paragraph.textContent = content;
        article.appendChild(paragraph);
        messages.appendChild(article);
        article.scrollIntoView({{ block: "end", behavior: "smooth" }});
        return article;
      }}

      function appendCitations(container, citations) {{
        if (!Array.isArray(citations) || citations.length === 0) {{
          return;
        }}

        const list = document.createElement("ol");
        list.className = "citations";

        citations.forEach((citation) => {{
          const item = document.createElement("li");
          const title = citation.url
            ? (() => {{
                const link = document.createElement("a");
                link.href = citation.url;
                link.target = "_blank";
                link.rel = "noreferrer";
                link.textContent = citation.title;
                return link;
              }})()
            : document.createTextNode(citation.title);

          item.appendChild(title);

          if (citation.excerpt) {{
            const excerpt = document.createElement("p");
            excerpt.className = "muted";
            excerpt.textContent = citation.excerpt;
            item.appendChild(excerpt);
          }}

          list.appendChild(item);
        }});

        container.appendChild(list);
      }}

      form.addEventListener("submit", async (event) => {{
        event.preventDefault();
        const question = input.value.trim();
        if (!question) {{
          return;
        }}

        document.getElementById("empty-state")?.remove();
        appendMessage("user", question);
        input.value = "";
        submitButton.disabled = true;
        status.textContent = "Waiting for the posts chat API...";

        const requestBody = {{ question }};
        if (activeSessionId) {{
          requestBody.session_id = activeSessionId;
        }}

        try {{
          const response = await fetch(apiEndpoint, {{
            method: "POST",
            headers: {{
              "Content-Type": "application/json",
            }},
            credentials: "include",
            body: JSON.stringify(requestBody),
          }});

          if (!response.ok) {{
            throw new Error(`Request failed with ${{response.status}}`);
          }}

          const payload = await response.json();
          activeSessionId = payload.session_id ?? activeSessionId;

          const assistantMessage = appendMessage("assistant", payload.answer, payload.state);
          appendCitations(assistantMessage, payload.citations);
          status.textContent = activeSessionId
            ? `Conversation continues with session_id ${{activeSessionId}}.`
            : "Answered without a session id.";
        }} catch (error) {{
          appendMessage(
            "assistant",
            "The posts chat API is unavailable right now. "
              + "Try again after checking the upstream configuration.",
            "error",
          );
          status.textContent = error instanceof Error ? error.message : "Request failed";
        }} finally {{
          submitButton.disabled = false;
          input.focus();
        }}
      }});
    </script>
  </body>
</html>
"""
