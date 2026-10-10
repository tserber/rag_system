# Interview Prep — "Standard recording 38" (Python/Backend + ETL, data governance role, "core architecture team")

Context: two interviewers. First half = data governance/ETL background + Python fundamentals
(hashing, list/tuple internals, generators, context managers, async vs multiprocessing, GIL,
Flask/FastAPI/Django, REST, databases/ACID/indexes, ETL idempotency/migrations). Second half =
live coding (balanced-brackets checker). Interviewer flagged at the end that understanding
internal architecture (hash maps, memory) makes you "a better optimizer" — lean into that framing.

---

## 1. Background / self-introduction

**Q: Tell me about yourself / your background.**

> I'm a backend-focused Python developer with about 5 years of experience, spanning automation,
> data engineering, and backend development. Most recently I worked on ETL and data governance —
> gathering, transforming, and loading data from cloud sources, writing the SQL behind it, and
> building rule-based validation before a record is considered "clean." Before that I worked
> across automation/scraping and IoT-adjacent backend systems. Right now I also do freelance AI
> data-labeling/testing work. I'm Python-first, comfortable with Flask, FastAPI and Django, and
> I'm actively looking for a full-time backend role where I can go deeper on system design and
> architecture rather than staying purely at the scripting/ETL level.

**Likely follow-up:** *"Are you moving toward AI for governance/pipelines, or is it staying
rule-based?"* — Answer: rule-based/deterministic validation is still the right default for data
governance (predictable, auditable); AI/LLMs make sense for the non-deterministic parts
(fuzzy matching, free-text classification, anomaly review) but shouldn't replace deterministic
checks where correctness is verifiable in code.

---

## 2. Data structures & algorithms

**Q: How comfortable are you with data structures and algorithms?**
> Solid on the practical side — I use them daily (dicts, sets, generators). I'm weaker on
> classic interview-style algorithm puzzles (graph traversal, DP) and I'm actively practicing
> those on LeetCode.

**Q: Searching an element in a list — what's the time complexity?**
- Unsorted list: **O(n)** — linear scan, no shortcuts.
- Sorted list: **O(log n)** using **binary search** — repeatedly halve the search range by
  comparing the middle element. (Binary search is a general technique; a **Binary Search Tree**
  is a *different* data structure that gives O(log n) search *and* O(log n) insert, unlike a
  sorted Python list where insertion is O(n) because elements must shift.)

**Q: How does a Python dict work internally? Time complexity?**
> A dict is a **hash table**. Average case O(1) for get/set/delete — the key's hash determines
> a slot directly. Worst case is O(n) if there are many **hash collisions** (multiple keys
> hashing to the same bucket, forcing a fallback probe/chain). CPython's dict uses open
> addressing with pseudo-random probing, and has kept insertion order since 3.7.

**Q: Why must dict keys be hashable? What happens if you use an unhashable key?**
> Keys must be hashable (and hashability implies effectively immutable) because the hash value
> is computed once and used to find the bucket — if the key could mutate, its hash would change
> and the entry would become unreachable at its original bucket, silently corrupting the table.
> Using an unhashable key (e.g. a `list`) raises `TypeError: unhashable type: 'list'` immediately
> — Python refuses it rather than risk corruption. Tuples work as keys precisely because they're
> immutable (as long as their contents are also hashable).

**Q: Tuple vs list — memory/allocation behavior?**
> A tuple is immutable, so its exact size is known and fixed at creation — no extra capacity is
> reserved. A list is mutable and over-allocates some extra capacity so that repeated `.append()`
> calls are amortized O(1) instead of reallocating on every single append; when that headroom
> runs out, Python allocates a new, larger block and copies the contents over.

**Q: Anything beyond list/dict/tuple worth mentioning?**
> `collections` module — `deque` for O(1) append/pop from *both* ends (a plain list is O(n) for
> `insert(0, x)`), `Counter`, `defaultdict`, `OrderedDict`. Generators (`yield`) for lazy,
> on-demand iteration over large datasets without loading everything into memory. Context
> managers (`with`) for guaranteed cleanup (closing files, DB cursors) even on exceptions.

**Follow-ups worth pre-empting:**
- *Dict resizing*: when load factor gets high, CPython allocates a bigger table and rehashes —
  this is why identical-looking dict operations can occasionally cost more (amortized O(1) still
  holds on average).
- *Set* is the same hash-table idea as dict, just without values — same O(1) average membership
  test, same hashability requirement for elements.

---

## 3. Concurrency: async vs threading vs multiprocessing vs GIL

**Q: What have you used — async, multi-threading, multi-processing?**
> Mostly `async`/`await` for I/O-bound work (network calls, waiting on other services) —
> single-threaded, cooperative concurrency: while one coroutine is waiting on I/O, another runs.
> Multiprocessing I understand conceptually more than I've deeply implemented: it's the right
> tool for **CPU-bound** work, because the GIL means only one thread executes Python bytecode at
> a time — so multi*threading* doesn't help CPU-bound work, but multi*processing* does, since
> each process gets its own interpreter and GIL. On a 4-core machine, splitting CPU-heavy work
> across 4 processes can get close to a 4x speedup; batching data across worker processes is a
> common pattern for that.
> - Free-threaded CPython (PEP 703, experimental since 3.13) is starting to make GIL-free
>   multi-threading possible — worth mentioning if it comes up as a "what's next" question.

**Likely follow-up:** *"When would you pick threading over multiprocessing?"* — I/O-bound work
where you want shared memory without the serialization overhead of inter-process communication;
processes are heavier (separate memory space, pickling to communicate) but truly parallel for
CPU-bound work.

---

## 4. Flask vs FastAPI vs Django

**Q: Differences? How do you choose?**
> - **Flask** — minimal, fastest to stand up a simple endpoint or a one-off internal job. No
>   batteries included, so you assemble what you need.
> - **Django** — full-featured (ORM, admin panel, auth, migrations) — best when you need an
>   admin UI, a full ORM, or a lot of built-in structure quickly.
> - **FastAPI** — best when data validation matters: **Pydantic models** give you automatic
>   request/response validation, typed schemas, and free OpenAPI/Swagger docs. It's async-native
>   and has become my default for API-first services where the API surface itself is the
>   deliverable (as opposed to a full web app).

**Q: What do serialization and deserialization mean, in this context?**
> **Serialization** converts an in-memory Python object into a transportable format (JSON,
> typically) — e.g. turning a Pydantic model into the JSON response body. **Deserialization** is
> the reverse: parsing incoming JSON (or form data) into a validated Python object. Pydantic
> does both, and *validates* while doing it — checking field presence, types, and constraints —
> so a malformed request is rejected before it ever reaches your business logic.

**Q: Are REST APIs stateful or stateless? What's the difference?**
> REST is **stateless** by design — the server holds no session/client state between requests;
> every request carries everything needed to process it (auth token, parameters). This is what
> makes REST APIs horizontally scalable — any server instance can handle any request. Contrast
> with stateful protocols/sessions where the server remembers client context between calls.
> Other protocols worth naming if asked: **gRPC** (binary, contract-first via protobuf, great for
> internal service-to-service calls), **GraphQL** (client specifies exactly which fields it
> wants), **JSON-RPC**.

---

## 5. Databases

**Q: Postgres vs MariaDB — how do you decide?**
> Postgres is my default: strong standards compliance, rich type system (JSONB, arrays, native
> full-text search), and excellent support for complex queries/window functions. MariaDB/MySQL
> tend to be chosen for simpler read-heavy workloads, existing MySQL tooling/ecosystem, or
> managed-hosting cost reasons. If the team already has deep MySQL/MariaDB operational expertise,
> that often outweighs Postgres's feature edge.

**Q: What are ACID properties?**
> **A**tomicity, **C**onsistency, **I**solation, **D**urability.
> - **Atomicity** — a transaction is all-or-nothing. Classic example: transferring money between
>   two accounts is two writes (debit + credit) that must both succeed or both roll back —
>   otherwise money disappears or is duplicated.
> - **Consistency** — a transaction moves the database from one valid state to another, never
>   violating constraints (foreign keys, uniqueness) mid-flight.
> - **Isolation** — concurrent transactions don't see each other's uncommitted intermediate
>   state (governed by isolation levels — read committed, repeatable read, serializable).
> - **Durability** — once committed, a transaction survives a crash (write-ahead log/WAL).

**Q: Have you used database views? Indexes — how many/which columns, disadvantages?**
> Views: less hands-on experience — happy to say so honestly and follow with what I do know:
> a view is a saved, named query that can simplify a complex/repeated join for consumers without
> duplicating the underlying data.
> Indexes: index the columns that are actually filtered/joined/sorted on most often — not every
> column. **B-tree is the default** index type in Postgres and covers most cases (equality,
> range queries); specialized types exist for specific needs — **GIN** for full-text/array/JSONB
> containment, **GiST** for geometric/range types, **BRIN** for huge, naturally-ordered tables.
> **Disadvantage of indexing**: every index must be updated on every insert/update/delete, so
> more indexes = slower writes and more storage — indexes trade write speed for read speed, so
> they should be added deliberately, not on everything.

**Q: ETL migration scenario — crash mid-run, how do you resume safely without duplicating or
corrupting records?**
> Make the write **idempotent** — an `UPSERT` (`INSERT ... ON CONFLICT DO UPDATE` in Postgres)
> keyed on a natural or synthetic unique key means re-running a batch that partially succeeded
> just overwrites with the same result rather than duplicating. On top of that, maintain a
> **ledger/checkpoint table** of batch status (`pending` / `in_progress` / `done` / `failed`) so
> a resumed run only reprocesses batches that didn't reach `done` — it doesn't burn time and
> resources redoing already-completed work.

**Q: Handling different schemas between source and target?**
> If it's a pure data move with a structural mismatch, map into a normalized/star schema and
> either backfill missing columns with nulls/defaults (if target has more columns) or split into
> multiple related tables joined by keys (if source has more granularity than target expects).
> The one thing to avoid is silently dropping data to force-fit a schema — better to flag the
> mismatch and require an explicit mapping decision than lose information silently.

**Q: How do you prevent race conditions between parallel migration workers?**
> A few complementary approaches: (1) partition work up front so each worker owns disjoint
> batches (no shared mutable state to race over) — this is usually the cleanest; (2) where
> workers *must* touch overlapping data, use row-level locking (`SELECT ... FOR UPDATE`) or a
> semaphore/distributed lock around the critical section; (3) rely on the idempotent
> upsert-by-key from the resume-safety answer above as a safety net even if a race slips through.

**Q: What if a security policy changes after approval but before activation?**
> Treat it as a new change requiring re-approval — approval is tied to the *specific* policy
> content that was reviewed; if the content changes, the prior approval no longer applies to
> what's about to be activated. This is standard change-control practice, not just a database
> question.

**Q: Processing a multi-GB file when memory is limited?**
> Stream it — read and process in chunks via a generator (or `pandas.read_csv(chunksize=...)`)
> instead of loading the whole file into memory at once. Process/write each chunk, discard it,
> move to the next.

---

## 6. Live coding: Balanced brackets

**Task:** given a string of `()[]{}`, determine if brackets are balanced (matched *and* properly
nested).

The interview attempt used a flawed counter-per-bracket-type approach that couldn't catch
ordering issues (e.g. `[(])` counts as balanced but isn't properly nested). The interviewer's own
hint — use a **stack** — is the standard, correct solution:

```python
def is_balanced(s: str) -> bool:
    pairs = {')': '(', ']': '[', '}': '{'}
    opening = set(pairs.values())
    stack: list[str] = []

    for ch in s:
        if ch in opening:
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        # non-bracket characters are ignored

    return not stack  # any unmatched opens left over -> unbalanced
```

Why it works: push every opening bracket; on a closing bracket, it must match the *most
recently* pushed unmatched opener (last-in-first-out — exactly what a stack gives you) — pop and
compare. Any mismatch, or a closer with nothing to match, means unbalanced. At the end, leftover
unclosed openers also mean unbalanced. **O(n) time, O(n) worst-case space.**

**Likely follow-ups:**
- *"What if there are other characters mixed in (letters, spaces)?"* — already handled: anything
  not a bracket is just skipped.
- *"Can you do it without a stack?"* — not correctly, in general, without reinventing one; a
  pure counter can't detect ordering violations like `[(])`.
- *"Recursive version?"* — possible but stack/iterative is clearer and avoids recursion-depth
  limits on long strings.

---

## 7. Closing / "what are my gaps" questions

The interviewer declined to give live feedback but hinted the deeper-architecture questions
(hash internals, memory/heap behavior) are where extra depth helps most — a good self-directed
study angle: CPython internals (how dict/list are implemented under the hood — `CPython
internals` book or the CPython source `Objects/dictobject.c`), `memoryview`/buffer protocol, and
the removal of the GIL (PEP 703) as a forward-looking talking point.

**Possible additional questions to prepare for (not asked here, but adjacent):**
- SQLAlchemy / ORM vs raw SQL tradeoffs.
- Connection pooling, and why it matters under load.
- Transaction isolation levels and what problem each solves (dirty read, non-repeatable read,
  phantom read).
- Exactly-once vs at-least-once processing semantics in pipelines.
- `dataclasses` / `pydantic` vs plain classes for data containers.
