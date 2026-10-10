# Interview Prep — "veeam tech" (Veeam Software, QA Automation Engineer)

Context: Veeam is a backup/data-protection company (~6,000 people, ~90 in this QA dept). Role is
QA automation in Python, testing backup/restore across many platforms (Windows/Linux/Mac,
vSphere, AWS/Azure/GCP/IBM Cloud, Office 365/Salesforce SaaS backup), with GitLab/TFS + Jenkins
CI/CD, MS SQL/Postgres. Interview = warm-up math/networking questions, two live coding tasks
(a range-printing exercise, then binary-tree traversal), a file-handling/context-manager
discussion, and a QA test-case design exercise on a login/connect desktop app.

---

## 1. Warm-up questions

**Q: Which is greater, 2/3 or 3/5?**
> Convert to a common denominator (15): 2/3 = 10/15, 3/5 = 9/15. **2/3 is greater.**
> *(The candidate answered this correctly live — just restating cleanly for confidence.)*

**Q: Convert 7/4 of a minute to seconds.**
> 1 minute = 60s, so 1/4 minute = 15s, and 7 × 15s = **105 seconds = 1 minute 45 seconds.**
> *(Also answered correctly live.)*

**Q: What is DHCP?**
> **Dynamic Host Configuration Protocol** — automatically assigns an IP address (plus subnet
> mask, default gateway, and DNS server info) to a device when it joins a network, so devices
> don't need manual IP configuration. *(The candidate mixed this up with DNS live — worth having
> both crisply separated: DHCP assigns addresses; DNS resolves names to addresses.)*

**Q: What is DNS?**
> **Domain Name System** — resolves human-readable domain names (google.com) to IP addresses,
> so browsers/clients know which server to connect to. Works via a hierarchical, distributed
> system of DNS servers that can recursively query each other to resolve a name.

**Q: Windows Registry — what is it?**
> A hierarchical database Windows and installed applications use to store configuration settings
> (system settings, per-user preferences, installed software info) — edited via `regedit`
> (Run → `regedit`). *(Candidate hadn't worked with it — honest "more Linux/PowerShell background"
> answer is fine; know the one-liner for next time.)*

**Q: Linux/Unix file permissions and access control — how would you make a downloaded binary
executable?**
> `chmod +x filename` adds the execute bit. More generally, `chmod` sets read/write/execute
> permissions for owner/group/others (numeric form e.g. `chmod 755 file`), and `chown` changes
> file ownership. Elevated changes typically need `sudo`.

**Likely follow-up (not asked but natural extension):** *"TCP vs UDP — which does DHCP/DNS use?"*
— DHCP uses UDP (broadcast-based discovery before a full connection can be established); DNS
primarily uses UDP for fast lookups, falling back to TCP for larger responses (e.g. zone
transfers).

---

## 2. Background walkthrough

**Q: Tell me about the most difficult/complex project — technologies, what you did.**
> Most relevant experience: automation QA at Ajax — testing an embedded security hub, the device
> that controls all sensors/units in the system and talks to the backend server. Built tests
> against the hub, wrote mocks for the server and for connected devices, worked with **UART**,
> **Telnet**, and async communication protocols. Also did log parsing at scale — a rolling-window
> approach to extract errors/intrusions from logs gathered across many hubs ("farms" of devices).
> Later helped build a **BDD** layer so the QA team could write new device tests declaratively
> (pass in a device + expected behavior) rather than hand-coding each one — because new
> hardware devices shipped every few weeks and each needed test coverage fast.

---

## 3. Live coding task 1 — range/FizzBuzz-style exercise

*(Transcript detail on the exact custom rule — a "print Jackie Chan" variant over a numeric
range — wasn't fully captured in the recording, so the precise trigger condition can't be
reconstructed reliably here. Worth reviewing your own memory of this specific exercise before a
repeat interview. The general pattern is standard FizzBuzz-style: iterate a range, and for each
number apply conditional string-substitution rules (e.g. divisible by X → print a fixed string
instead of the number). If it recurs, structure it as:*

```python
def custom_fizzbuzz(start: int, end: int) -> None:
    for n in range(start, end + 1):
        # replace with the actual rule set once confirmed
        if n % 15 == 0:
            print("FizzBuzz")
        elif n % 3 == 0:
            print("Fizz")
        elif n % 5 == 0:
            print("Buzz")
        else:
            print(n)
```
*Keep it simple, iterative, and get a passing baseline before refactoring to a dict-driven rule
table (which is the natural "make it more extensible" follow-up for this style of task).*

---

## 4. Live coding task 2 — binary tree traversal ("cat names")

**Task:** given a binary tree of nodes (each with a name attribute, plus `left`/`right` child
references), traverse from the root and print all the names.

**Clean recursive solution (DFS, pre-order):**
```python
def print_names(node) -> None:
    if node is None:
        return
    print(node.cat_name)
    print_names(node.left)
    print_names(node.right)
```

**Iterative version (explicit stack — avoids recursion-depth limits):**
```python
def print_names_iterative(root) -> None:
    stack = [root] if root is not None else []
    while stack:
        node = stack.pop()
        print(node.cat_name)
        if node.right is not None:
            stack.append(node.right)
        if node.left is not None:
            stack.append(node.left)  # push left last so it's popped first
```

**Q: What's the potential problem with the recursive approach?**
> Two things: (1) if the structure isn't a true tree but has a **cycle** (e.g. a node's child
> pointer loops back to an ancestor), naive recursion never terminates — a `visited` set keyed
> by node identity is needed to guard against that if cycles are possible; (2) very deep trees
> can hit Python's recursion limit — the iterative/stack version sidesteps both problems.

**Likely follow-up:** *"BFS instead of DFS?"* — Use a `collections.deque` as a FIFO queue instead
of a stack (`popleft()` instead of `pop()`) to traverse level-by-level instead of depth-first.

---

## 5. File handling / context managers

**Q: What does `with open(...)` give you that a plain `open()`/`close()` doesn't?**
> Guaranteed cleanup: the file is closed automatically when the `with` block exits, **even if an
> exception happens inside it** — because a context manager's `__exit__` runs during exception
> unwinding, not just on normal completion. Plain manual `open()`/`.close()` skips the close if
> an exception happens between them, unless wrapped in `try/finally` — the `with` statement is
> exactly that pattern, built in.

**Q: Why do we need to close a file at all — what happens if we don't?**
> An open file keeps a handle/resource held by the OS (and internal buffers un-flushed) for as
> long as the process runs — not closing it leaks file descriptors, which is a real problem in
> long-running processes with many file operations (eventually hits the OS's per-process file-
> descriptor limit), and buffered writes may never actually reach disk if the handle isn't closed
> or explicitly flushed.

**Q: A large file lives on a USB drive; you start reading it, then the drive disconnects mid-
read. What happens — compare a version using `with open(...)` vs. a version that opens without a
context manager and no error handling?**
> Either way, the read call itself will raise an exception once the underlying storage becomes
> inaccessible (an `OSError`/`IOError` on the next read call). The difference is what happens
> *around* that exception:
> - **With a context manager, but no `try/except` around the read**: the exception still
>   propagates up and stops the program — a context manager doesn't swallow exceptions by
>   default, it *guarantees cleanup* (file handle closed) as the exception unwinds. Without a
>   `try/except`, the program crashes at that line either way.
> - **Without a context manager and without error handling**: same crash, *plus* the file handle
>   is never explicitly closed (though the OS typically reclaims it on process exit or garbage
>   collection eventually — this isn't reliable to depend on).
> - To actually **survive** the disconnect and continue: wrap the read in `try/except`, handle
>   the specific exception (log it, retry, or gracefully abort just that file), and keep the
>   `with` block for guaranteed cleanup regardless of which path is taken:
>   ```python
>   try:
>       with open(path) as f:
>           data = f.read()
>   except OSError as e:
>       log.error(f"Failed reading {path}: {e}")
>       data = None
>   ```
> A `try/except` *alone*, without something after it, only stops the crash at that point — the
> program still needs an explicit next step (a default value, a retry, a skip-and-continue) to
> actually keep going in a useful way, which is exactly the missing piece the interviewer was
> steering toward.

---

## 6. QA test-case design — login/connect desktop application

**Scenario:** a Windows desktop app with fields **Server / Login / Password**, buttons
**Connect / Close / Help**. Successful connection persists the server in a dropdown for next
launch.

**A well-organized answer, structured by category (this structure itself is worth stating out
loud — it shows a systematic QA mindset, not just an ad-hoc list):**

1. **Field combinations / equivalence classes** — each field individually filled vs. empty,
   pressing Connect in every combination (server-only, login-only, password-only, all filled,
   none filled) — verify correct validation messaging for each incomplete case.
2. **Input validation / boundary values** — invalid characters (Unicode, emoji, whitespace-only,
   extremely long strings) in each field; whether Password is masked; whether Login accepts
   values that look like it shouldn't (format checks).
3. **Success path & persistence** — valid credentials → Connect succeeds → relaunch app → server
   now appears in the dropdown. **Duplicate check**: connect twice to the *same* server — does
   it get added to the dropdown twice? (Flagged as a strong test case during the actual
   interview — good one to lead with.)
4. **Failure path & error messaging** — wrong login vs. wrong password should ideally produce
   distinguishable, accurate error messages (don't just say "connect failed" if the app can tell
   you *which* field was wrong) — check Help button surfaces context-appropriate guidance for
   each failure type.
5. **Dropdown scale/UI robustness** — many saved servers (e.g. 20+): is the list scrollable, or
   do later entries become inaccessible? Deleting a saved server — does it leave a blank/ghost
   entry, or clean up properly?
6. **Window controls** — Close button and the window's "X" — both should fully terminate the
   process if there's no active connection (verify via process list, not just "window
   disappeared" — the process could still be running in the background). Behavior should differ
   appropriately if a connection *is* active (e.g. confirm-before-close).
7. **Reconnect / already-in-dropdown flow** — selecting an existing saved server from the
   dropdown and connecting "hot" vs. entering the same details "cold" — do both paths behave
   consistently?
8. **Out-of-scope but worth flagging explicitly**: anything about what happens *on the backup/
   replication server itself* is out of scope for this desktop-app testing task — good to state
   that boundary out loud so the interviewer knows you're not confusing app-level and
   server-level testing.

**Likely follow-ups on this exercise:**
- *"How would you automate these?"* — Page Object Model for the desktop UI (or its equivalent for
  desktop automation tooling), data-driven test cases for the equivalence-class matrix, separate
  smoke suite (core connect/close path) from full regression (edge cases/Unicode/scale).
- *"How would you prioritize which of these to automate first vs. leave manual?"* — Automate the
  high-frequency, stable paths first (login success/failure, persistence); leave low-frequency
  exploratory cases (Unicode edge cases, huge dropdown scale) as manual/exploratory testing
  initially, automate once they've proven valuable to repeat.
