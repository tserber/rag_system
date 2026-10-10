# Interview Prep — "Standard recording 35" (Intelius, AI/RAG Engineering)

Context: technical interview for Intelius (consulting/engineering company, client-staffed model).
Interviewer David went deep on a real-estate valuation RAG project, then AI-engineering breadth
(agent tools, tokenization, temperature, RAGAS/LLM-as-judge, search types, agentic design
patterns). At the end he explicitly named the **gaps**: agentic design patterns, tokenization
detail, the three search types, and evaluation frameworks (RAGAS, LLM-as-judge) — those are
covered thoroughly below since they're the most likely to resurface.

---

## 1. Background / project walkthrough

**Q: Tell me about yourself and your AI-related work.**
> Background started in radio engineering, moved into automation/backend, and most recently into
> AI-adjacent backend work: a data-mocking framework (generating realistic synthetic data when a
> business has no database of its own yet, feeding a third-party analytics/dashboard layer), and
> — most relevant here — a **RAG system for a real-estate valuation company**: a large volume of
> valuation documents needed to be classified, chunked, embedded, and made retrievable so that a
> new valuation could reuse similar historical examples as grounding context instead of starting
> from scratch.

**Q: Walk me through the RAG project end-to-end — data layer, ingestion, retrieval, evaluation.**
> - **Document variance**: templated documents parse easily (fixed field positions); non-standard
>   ones needed different handling per structure.
> - **Chunking**: naive fixed-size chunking (e.g. 500–1000 words) is fast but risks splitting
>   context mid-thought and losing scale/units information stated earlier in the document (a
>   real bug I hit: a document stated "all values in thousands" once near the top, and a chunk
>   further down just said "35" — without that earlier context carried forward, it was
>   interpreted as 35 instead of 35,000). Better approaches, in increasing sophistication:
>   1. Chunk by structural boundaries (paragraphs/sections) using a document-parsing library
>      rather than a raw word count.
>   2. Chunk by size close to but under the embedding model's context window, with overlap
>      (~50–100 words) so context isn't hard-cut at boundaries.
>   3. Run a first LLM pass to extract document-level metadata (units, dates, parties) and
>      attach it to every chunk from that document, so scale/units survive chunking.
> - **Tables**: extracted programmatically (parsing libraries for structured PDF tables), kept
>   in metadata for on-demand retrieval when a table is large.
> - **Metadata**: date created, date processed, and other document-level facts attached to every
>   chunk — critical for a valuation use case where recency and provenance matter.
> - **Retrieval validation**: two-call pattern — one LLM call retrieves, a second call checks
>   whether the retrieved content is actually consistent with/relevant to the query, catching
>   retrieval drift before it reaches the user.

**Likely follow-up:** *"What metric did you use to validate accuracy for stakeholders?"* — Be
honest that a formal metrics dashboard wasn't in place on that project, but describe what the
right approach is: retrieval quality (precision@k — of the top-k returned chunks, how many are
actually relevant to a labeled query set), and end-to-end answer quality via an LLM-as-judge
comparing generated vs. expected answers on a held-out golden set, re-run on every deployment
(not on every live query — too expensive/slow for that).

---

## 2. Chunking, tables, OCR

**Q: How do you handle scanned/image documents?**
> Wasn't needed on that project (single-language, single-country, mostly digital-native docs),
> but the standard approach: OCR (Tesseract, or a layout-aware document AI service) to get text,
> then a classification step to detect whether OCR actually succeeded cleanly (garbled output,
> low-confidence characters) before trusting the extracted text downstream.

---

## 3. Search types — the flagged gap

**Q: What are the different types of search / retrieval?**
> Three complementary types, and they're often combined (**hybrid search**):
> 1. **Keyword / lexical search** (e.g. BM25) — exact/fuzzy term matching, strong for exact
>    identifiers, names, codes — things where the precise wording matters.
> 2. **Semantic / vector search** — embed the query and the documents into the same vector space
>    and retrieve by similarity (cosine/dot product); catches meaning-based matches even when the
>    wording differs completely.
> 3. **Metadata / structured filtering** — filter by fields like date, document type, region
>    before (or combined with) the above, to narrow the candidate pool using facts you already
>    know rather than relying on the model to infer them from text.
> **Hybrid search** combines keyword + vector results — commonly via **Reciprocal Rank Fusion
> (RRF)** to merge the two ranked lists — because keyword search catches exact-term cases vector
> search sometimes misses, and vice versa.

---

## 4. Tokenization, context window, temperature — the flagged gap

**Q: What is tokenization?**
> The process of converting raw text into discrete units (**tokens**) the model can process
> numerically — tokens are usually sub-word pieces (via BPE or similar), not whole words; a
> word can be one token or split into several depending on how common it is in the training
> vocabulary.

**Q: What's the difference between a context window and tokens more generally?**
> A **token** is the unit of text the model consumes. The **context window** is the maximum
> number of tokens (input + output combined, depending on the model) the model can attend to in
> a single call — exceed it and older content gets truncated or the call fails. Tokens are also
> the unit of **pricing** (cost scales with tokens in + tokens out) and of latency (more tokens
> generally means more compute).

**Q: What does temperature control?**
> How deterministic vs. creative/random the output sampling is. Low temperature (near 0) makes
> the model consistently pick the highest-probability next token — good for factual/extraction
> tasks where you want repeatable output. Higher temperature increases randomness/diversity in
> word choice — useful for creative generation, riskier for tasks needing accuracy since it
> raises hallucination risk.

**Q: How does an LLM process a token, at a high level?**
> The token is embedded into a vector, then passed through the model's stack of transformer
> layers — each layer applies learned attention weights (which other tokens in the context matter
> most for this one) and feed-forward transformations, refining the representation layer by
> layer, ultimately producing a probability distribution over the next token.

---

## 5. Evaluation frameworks — RAGAS / LLM-as-judge — the flagged gap

**Q: How do you evaluate a RAG system for stakeholders?**
> Build a golden set of representative questions with expected answers/expected retrieved
> context. Run the pipeline against it and score with:
> - **RAGAS** (or an equivalent framework) — standard RAG metrics: **faithfulness** (is the
>   answer actually grounded in the retrieved context, not hallucinated), **context
>   precision/recall** (did retrieval return the right chunks, and *only* the right chunks), and
>   **answer relevance**.
> - **LLM-as-judge** — a separate LLM call compares the generated answer against the expected
>   answer and the retrieved context, and can be instructed to justify its score (e.g. "answer is
>   missing key context" / "hallucinated a detail") — turning that into something like "92% of
>   100 test questions scored acceptable," a number a business stakeholder can actually act on,
>   without needing to understand precision/recall internals themselves.
> - Run this **on every deployment**, not on every live request — it's a regression gate, not a
>   runtime cost.

---

## 6. Agent design — tools, patterns, MCP

**Q: Why use multiple tools/functions with an agent? What's the benefit?**
> A single LLM call is limited to what it "knows"; giving it tools lets it take actions and pull
> in live/external information (query a database, call an API, run a calculation) as part of a
> reasoning loop — the agent decides which tool fits the current sub-goal, calls it, gets a
> result, and continues reasoning with that result added to context (optionally with a human in
> the loop for higher-stakes steps).

**Q: What is MCP (Model Context Protocol)?**
> A standardized way to expose tools/context/data sources to a model in a consistent, reusable
> interface — instead of every application wiring up bespoke function-calling glue, MCP servers
> expose a common protocol the model (and any MCP-compatible client) can consume, so tools become
> plug-and-play across different agents/assistants rather than one-off integrations.

**Q: Agentic design patterns — how many do you know?**
*(Flagged gap — worth having 4–5 ready by name:)*
> - **Chain** — a fixed sequence of agents/steps, output of one feeds the next.
> - **Supervisor / orchestrator–worker** — one supervisor agent interprets the user's goal and
>   delegates sub-tasks to specialized sub-agents (this is how many coding assistants like Claude
>   Code are structured).
> - **Reflection** — the agent critiques/reviews its own output and iterates before returning a
>   final answer.
> - **Planner–executor** — a planning step decomposes the goal into steps up front, then an
>   executor works through them (vs. reasoning step-by-step live, as in ReAct).
> - **ReAct (Reason+Act)** — interleave reasoning traces with tool calls, observing each result
>   before deciding the next action.
> - **Human-in-the-loop** — an explicit checkpoint where a person approves/edits before a
>   higher-risk action proceeds (this is exactly the pattern used in the real-estate-doc RAG
>   project's email-taxonomy validation).

**Q: Taxonomy classification from customer emails — how would you engineer it, and how would you
validate the output isn't hallucinating?**
> - **Design**: first-level classification (which team: bookings/food/transport/activities) via
>   an LLM call constrained to a fixed enum of valid categories (never let the model invent a
>   category name — always classify against a closed, versioned list); second-level
>   classification within that team's existing FAQ/question set. Enforce **structured output**
>   (JSON mode / function-calling schema) so the response is directly parseable, not free text.
> - **Validation**: (1) hard-validate the JSON shape/keys/types in code (Pydantic) before
>   accepting it; (2) if the model claims "no injection" but returns malformed output, reject and
>   retry with a corrective prompt; (3) human-in-the-loop review for genuinely new/unmatched
>   questions early on, replaced over time by a second LLM call that checks new classifications
>   against the existing question/answer bank for consistency, reducing human review as the
>   system earns trust.

**Q: RAG vs fine-tuning — when do you choose one over the other?**
> Fine-tuning needs a large labeled dataset (with a held-out eval split) and ongoing MLOps to
> retrain as the domain changes — it's expensive to set up and to keep current, but can be worth
> it for style/format adaptation or very narrow, stable domains. RAG needs no retraining to add
> new information — updating the knowledge base is enough — trades some in-context reasoning
> overhead (retrieval + longer prompts) for freshness and much lower setup cost. For domains
> where facts change often (real-estate valuations, customer support knowledge bases), RAG is
> almost always the better fit; fine-tuning is better suited to teaching a *behavior/format*
> rather than *facts*.

**Q: Make an AI system faster, cheaper, and more secure — what levers do you pull?**
> - **Faster/cheaper**: cache answers to frequent/common questions so repeat queries skip the
>   LLM call entirely; pick a smaller/faster model where quality allows; watch time-to-first-token
>   (a model that "thinks" a long time before responding may need swapping for a faster one).
> - **Secure**: apply least-privilege to whatever tools/data the agent can touch — read-only vs.
>   write/delete access, scoped by user role (admin vs. regular user) via metadata-based access
>   control on the documents/functions themselves, not just at the UI layer.

---

## 7. Python fundamentals asked in this interview

**Q: `*args` vs `**kwargs`?**
> `*args` collects extra **positional** arguments into a tuple; `**kwargs` collects extra
> **keyword** arguments into a dict. Both let a function accept a variable/unknown number of
> arguments.

**Q: Functions vs. classes — when do you reach for which?**
> Functions for simple, stateless transformations. Classes when you need to bundle state with
> behavior, or want **inheritance** (reuse/extend behavior from a parent), **encapsulation**
> (hide internal details behind a clean interface), and **polymorphism** — those give structure
> and reusability that a pile of standalone functions doesn't. Neither is strictly better; classes
> add useful structure at the cost of more ceremony for something genuinely simple.

**Q: Best practices when writing code?**
> Define test cases and edge cases before writing the implementation — clarifies the actual
> contract. Prefer readable multi-line code over "clever" one-liners that are hard to review.
> Use linting/formatting (`black`) and a type checker consistently. Reach for established patterns
> (e.g. Builder) where they fit rather than reinventing structure. Before extending a system,
> look at what comparable systems do well and take the good parts rather than just extrapolating
> from scratch.

---

## 8. Possible additional questions to prepare for

- "What's the difference between prompt engineering techniques — zero-shot, few-shot, chain-of-
  thought, instruction-following?" (interviewer named these explicitly as important — have one
  line on each ready: zero-shot = no examples given; few-shot = a handful of examples in-prompt;
  chain-of-thought = ask the model to reason step-by-step before answering, improves multi-step
  accuracy; instruction-following = models fine-tuned specifically to follow explicit directives
  reliably.)
- "How would you reduce hallucination in a structured-output pipeline beyond schema validation?"
  — grounding citations back to source chunks, constrained decoding/JSON mode, lower temperature.
- "How do you handle PII in a RAG pipeline over customer emails?" — redaction/masking before
  embedding, access-scoped retrieval, audit logging.
- "Vector database choice — how would you pick one?" — throughput/latency needs, hybrid-search
  support, metadata filtering support, managed vs. self-hosted tradeoffs.
