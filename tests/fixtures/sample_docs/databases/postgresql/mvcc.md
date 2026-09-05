# PostgreSQL: MVCC and concurrency

PostgreSQL uses Multi-Version Concurrency Control (MVCC) to handle concurrent
access without locking readers out of writers. Each transaction sees a
consistent snapshot of the database. Instead of overwriting rows in place,
an UPDATE creates a new row version and marks the old one as dead; VACUUM
later reclaims space from dead tuples.
