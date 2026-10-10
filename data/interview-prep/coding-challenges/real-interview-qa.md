# Interview Prep — "Standard recording 23" (Google-style live coding: word predictor)

Context: live coding interview with Gustavo (Google). Task: design and build a "word predictor"
— given training data (list of sentences, already tokenized into words) and an input word,
return the most frequent word that follows it in the training data. Must be optimized for **fast
repeated prediction** (interviewer explicitly said prediction happens "a lot of times" — so
precompute once, don't rescan training data per prediction).

The live attempt got there eventually via a nudge toward precomputing a lookup structure, but ran
out of time before finishing cleanly. Below is the clean, complete solution plus the reasoning
the interviewer was steering toward.

---

## The clean solution

```python
from collections import defaultdict, Counter

def build_predictor(training_data: list[list[str]]) -> dict[str, str]:
    """
    One-time preprocessing: for every word, count how often each possible
    'next word' follows it across the whole training set, then keep only
    the most frequent successor. O(total words) time and space.
    """
    successor_counts: dict[str, Counter] = defaultdict(Counter)

    for sentence in training_data:
        for current_word, next_word in zip(sentence, sentence[1:]):
            successor_counts[current_word][next_word] += 1

    # Collapse each word's Counter down to just its single best successor
    # so that prediction is a plain O(1) dict lookup.
    return {
        word: counts.most_common(1)[0][0]
        for word, counts in successor_counts.items()
    }


def predict_next(word: str, predictor: dict[str, str]) -> str | None:
    """O(1) prediction. None if the word was never seen, or never had a successor."""
    return predictor.get(word)
```

**Why this is the right shape:**
- **Training data doesn't change** (confirmed in the interview) — so all the expensive scanning
  work belongs in a one-time `build_predictor` call, not in the hot prediction path. This is
  exactly the "transpose the data" hint the interviewer was steering toward: build a
  `word -> best next word` lookup once, then every `predict_next` call is **O(1)**.
- Using `Counter` per word cleanly handles duplicates (multiple occurrences of the same
  `word -> next_word` pair across sentences) — that was one of the candidate's own good
  questions during the interview, and this is the clean answer to it.
- `zip(sentence, sentence[1:])` is the idiomatic, allocation-light way to iterate consecutive
  word pairs without manual indexing.

---

## Edge cases (the interviewer's follow-ups, answered cleanly)

**Q: What if the word was never seen in training data?**
> `predictor.get(word)` returns `None` — explicit "no data" signal, and the caller decides how
> to surface that (error message, empty string, log-and-skip) depending on how the API is
> consumed. `None` is preferable to raising by default, since "unknown word" is an expected,
> normal outcome, not an exceptional one.

**Q: What if the word has no successor (e.g. it's always the last word of a sentence)?**
> Same answer — it simply never gets added as a key in `successor_counts`, so `.get()` returns
> `None` naturally. No special-casing needed.

**Q: How do you break ties when two candidate next-words have the same frequency?**
> `Counter.most_common(1)` breaks ties by **insertion order** — whichever candidate word was
> first encountered during training wins. That's a real design decision worth stating out loud
> rather than leaving implicit — if a different tie-break rule is wanted (alphabetical, most
> recent), that should be explicit in the code, e.g.
> `min(counts.items(), key=lambda kv: (-kv[1], kv[0]))` for "alphabetically first among the
> ties."

---

## Complexity

- **Build**: O(N) time and space, where N = total word count across all training sentences —
  one pass over the data.
- **Predict**: O(1) — a single dict lookup.

This is the direct answer to "we should optimize for the fastest possible prediction time" —
all the cost is paid once, up front, not on every call.

---

## Possible additional/follow-up questions

- **"Extend this to look two words back (trigram model) instead of one."** — Key becomes a tuple
  `(word_before_prev, prev_word)` instead of a single word; same `Counter`-per-key approach
  otherwise. This generalizes to an n-gram Markov chain of any order.
- **"How would you support incremental updates (add new training sentences without rebuilding
  everything)?"** — Keep `successor_counts` (the full Counter, not just the collapsed
  best-only dict) as the persisted state; on new data, just update the relevant Counters and
  recompute `most_common(1)` only for the affected words, not the whole predictor.
- **"Memory concerns for a huge vocabulary?"** — The full `successor_counts` structure can get
  large (effectively a sparse word x word co-occurrence table); for very large vocabularies,
  pruning rare/low-count entries, or using a more compact structure, becomes worth discussing.
- **"Thread safety if this is called concurrently?"** — Prediction is read-only against an
  immutable dict once built, so it's naturally safe for concurrent reads; only rebuilding/
  updating the predictor needs synchronization.
- **"Why not just store all successors and pick the max at prediction time instead of collapsing
  ahead of time?"** — That would move O(k) work (k = number of distinct successors for that
  word) into every prediction call instead of paying it once at build time — worse for a
  "predict is called a lot" workload, which is exactly the constraint given.
