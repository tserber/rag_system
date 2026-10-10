# Interview Prep — "chi" (Recruiter screening call, Ukrainian outsourcing/outstaff agency)

Context: HR screening call (in Ukrainian) with a recruiter at an outsourcing/outstaff company.
Covered background, cloud/DB experience, rate, availability, domain preferences, and — most
actionable — the recruiter's own **preview of what the technical interview will cover**. That
preview is the single most valuable thing to prepare from this call.

---

## 1. What the recruiter said the technical interview will actually cover

This is a direct preview from the recruiter (Ukrainian, paraphrased/translated) — treat this as
the prep checklist for the *next* interview:

- **Python**: which versions you've used, how they differ.
- **Databases**: which ones, how they differ, when each is the better fit (this matches exactly
  the Postgres/MariaDB/indexing material in [Standard recording 38 - Prep Answers.md](Standard%20recording%2038%20-%20Prep%20Answers.md)).
- **Cloud**: Azure and GCP specifically (recruiter noted AWS isn't on the CV, so it likely won't
  be probed) — services used, what for.
- **Git / CI-CD**: whatever's actually been used.
- **LLM / RAG pipeline / LangChain / LangGraph** — explicitly flagged as a strong area to prepare
  since it was mentioned as part of the pet project: what the pipeline did, why each tool choice,
  what worked well vs. what you'd do differently, how you'd improve specific parts of it.

**Pristine talking points for the pet-project RAG pipeline** (grounded in what was actually
described on the call — a small pet project storing client evaluation data across multiple
formats, feeding a RAG-style retrieval flow):
> The pet project stored client-evaluation data across a range of source formats, with the
> processed results feeding a RAG pipeline. The main design questions were: what to store and how
> to structure it for retrieval, and what to hand off to the AI layer, and in what shape. Good
> follow-up prep: be ready to state **why** each tool was chosen (LangChain/LangGraph vs. building
> the orchestration by hand), one concrete thing that worked well, and one concrete thing to
> improve if starting over — interviewers consistently respond better to a specific "here's what
> I'd change" than a purely positive account.

---

## 2. Background summary (as actually given on the call — useful to keep consistent across
interviews)

> ~5 years of Python. Recent work: a pet project storing/evaluating client data across formats,
> feeding results into a retrieval pipeline. Most recent professional role (70 Experts): data
> generation for a business without its own database/data sample — building the schema, then
> populating it, with a human-in-the-loop validation step at each stage rather than a fully
> autonomous agent (a person adds/confirms data at each step). Cloud: Google Cloud and Azure —
> S3-equivalent buckets/compute instances, mostly for SQL generation and data
> transformation/storage/movement. Also some automation QA background (~2 years) — mocking
> already-built functionality specifically to make it *breakable* for test purposes (the opposite
> mindset from development, where the goal is to make things *not* break).

---

## 3. Snowflake (recruiter flagged strong client demand for this)

> Experience: migrating existing data-processing/storage logic onto Snowflake — systematizing
> existing logic to fit Snowflake's model, adapting SQL, and using Snowflake-specific features
> (tasks, internal scheduling/orchestration) to reduce cost versus the prior setup. Used it more
> as a target database than as a deep specialist, worth stating honestly rather than overclaiming
> depth — and it's a good area to actively brush up on given the recruiter noted real client
> demand for Python + data engineering combined profiles.

---

## 4. Logistics / HR questions — talking points (not prescriptive numbers; adjust to current
preference)

**Q: Availability / job search status?**
> Actively looking, recently relocated to Poland, holds Karta Polaka (so no work-authorization
> blockers) — able to start promptly.

**Q: What are you looking for — project type / tech stack preference?**
> Open broadly — background spans data collection/processing, automation, and backend
> development, with backend development being where the most recent time has gone; genuinely
> interested in going deeper in that direction while staying open across the others.

**Q: Preferred working hours / time zone overlap?**
> Comfortable with US-hours overlap on evenings a few times a week if the project needs it, but
> not as an all-day default — flagged that an all-US-hours daily schedule mostly suits someone
> with no other evening commitments, which is a fair, honest boundary to state plainly rather
> than over-committing upfront.

**Q: Domain preferences (fintech, healthcare, etc.)?**
> Open to whatever's in active demand — fintech and healthcare were both named as genuinely fine;
> the one domain to flag as a pass is gambling (stated preference, not a hard technical
> constraint — worth restating clearly and early with any new recruiter to avoid a mismatch
> later).

**Q: Rate / compensation?**
> A concrete number (5,000 PLN gross) was floated as roughly the base to start the conversation
> from, open to a bit lower depending on the project scope, with room to revisit after the
> technical interview once level/fit is clearer — that's a reasonable structure to reuse: give a
> anchor number, stay flexible pending more project detail, and explicitly defer the final number
> to after the technical round rather than over-negotiating on a first call.

**Q: B2B contract (Polish B2B) — comfortable with it?**
> Yes, not yet formally set up but not expected to be a blocker; also open to Ukrainian FOP
> (invoicing as a Ukrainian private entrepreneur) as an alternative if that fits the project
> better — flexible on structure either way.

---

## 5. Process/logistics (for reference, not something to "answer")

- Recruiter flow: recruiter screening (this call) → short English check (~10–15 min, informal) →
  CV submitted to client → client-side interview(s) (sometimes a short intro call with a hiring
  manager first, then technical; occasionally a paid/unpaid test task depending on the client) →
  offer discussion, including revisiting rate after the technical round.
- The English check is genuinely informal — "just a conversation," not a test — no specific prep
  needed beyond normal spoken fluency.

---

## 6. Possible additional questions to prepare for at the next stage

Since the recruiter explicitly named these as the technical interview's focus areas, the highest-
leverage prep beyond what's already covered in the other prep files:
- **Python version differences** — be ready with concrete examples: walrus operator (3.8),
  structural pattern matching / `match` (3.10), improved error messages (3.11), performance
  improvements across 3.11–3.13, the experimental free-threaded (no-GIL) build (3.13+).
- **Why LangChain/LangGraph specifically, vs. building the orchestration directly against an LLM
  API?** — LangChain/LangGraph give ready-made abstractions for chains, memory, and multi-step
  agent graphs, trading a learning curve and some abstraction overhead for faster iteration and
  built-in patterns (retries, tool-calling glue) that would otherwise be hand-rolled.
- **CI/CD specifics** — which platform (GitLab CI, GitHub Actions, Jenkins), and one concrete
  pipeline you set up or maintained.
