# Databases — additional possible questions

Supplementary to qa-bank.md.

### What are transaction isolation levels, and what does each actually prevent?
They control how much one transaction can see of another's uncommitted or
concurrent changes. From loosest to strictest: **Read Uncommitted** (can
see uncommitted changes from others — "dirty reads"), **Read Committed**
(only sees committed data, but a value can change between two reads in
the same transaction — "non-repeatable read"), **Repeatable Read** (the
same row stays consistent for the whole transaction, but a new matching
row can appear on a re-run query — "phantom read"), **Serializable**
(transactions behave as if run one at a time). Postgres defaults to Read
Committed; higher levels cost more in locking/retry overhead.

### When would you reach for a NoSQL store (MongoDB, Redis) instead of Postgres?
Redis: when you need sub-millisecond access to simple key-value or
cache-shaped data, or pub/sub, not relational queries. MongoDB: when your
data is genuinely document-shaped with a schema that varies a lot between
records and you rarely need cross-document joins. The honest default is
still Postgres — it handles JSONB well enough to cover a lot of what
people reach for Mongo for, with transactional guarantees Mongo didn't
reliably have until relatively recently.

### What is connection pooling, and why does it matter?
Opening a new database connection is expensive (TCP handshake, auth,
process/memory setup on the DB side). A connection pool keeps a set of
already-open connections ready to hand out to the application, reusing
them across requests instead of opening/closing one per request. This
matters a lot for Postgres specifically, since each connection there is a
full OS process — see `PgBouncer` in qa-bank.md for the standard tool.

### What is denormalization, and when is it a reasonable tradeoff?
Deliberately duplicating data (instead of normalizing it into separate
linked tables) to avoid expensive joins on a hot read path — e.g. storing
a `comment_count` column on a post instead of `COUNT()`-ing comments every
time. It's reasonable when read performance genuinely matters more than
write simplicity and you accept the burden of keeping the duplicate copy
in sync (often via a trigger or application-level update).

### How do you run a schema migration on a large production table without downtime?
Avoid operations that take a long-held exclusive lock on the whole table.
Add a new nullable column instead of a `NOT NULL` column with a default
(which historically rewrote the whole table); backfill the column in
small batches; add constraints (`NOT NULL`, foreign keys) only after the
backfill, using `NOT VALID` + `VALIDATE CONSTRAINT` in Postgres so
validation doesn't hold a long lock either. Always test the migration's
lock behavior against a copy of production-sized data before running it
for real.
