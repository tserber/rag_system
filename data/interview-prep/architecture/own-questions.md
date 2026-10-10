# Architecture — additional possible questions

Supplementary to qa-bank.md.

### Horizontal vs. vertical scaling — what's the difference, and which do you default to?
Vertical scaling means a bigger machine (more CPU/RAM on the same box);
horizontal scaling means more machines sharing the load. Vertical is
simpler (no distributed-systems complexity) but has a hard ceiling and a
single point of failure. Horizontal scales further and survives a single
instance dying, at the cost of needing the application to actually be
stateless/shareable (shared sessions, shared cache, idempotent retries).
Default to vertical until you've actually hit its ceiling or need the
redundancy — horizontal scaling isn't free architecturally.

### How do you design a system to survive one dependency failing?
A few complementary patterns: **timeouts** on every external call (never
wait forever), **retries with backoff** for transient failures, a
**circuit breaker** that stops calling a dependency that's clearly down
instead of piling up failing requests, and **graceful degradation** —
decide in advance what the system does when a non-critical dependency is
unavailable (show cached/stale data, skip a non-essential feature) rather
than failing the whole request.

### Synchronous vs. asynchronous communication between services — how do you choose?
Synchronous (a direct REST/gRPC call, caller waits for the response) is
simpler to reason about and right when the caller genuinely needs the
result before it can continue. Asynchronous (a message queue, caller
publishes and moves on) decouples the services in time — the receiver
doesn't need to be up right now — and is the better fit for anything that
doesn't need an immediate response (sending a notification, processing an
order in the background) or where you want to absorb a traffic spike
rather than have it cascade into every downstream service.

### What's the Saga pattern, and why does it exist?
A way to handle a transaction that spans multiple services, where a
classic ACID transaction isn't possible because no single database owns
all the data. Instead of one atomic commit, a saga is a sequence of local
transactions, each with a defined *compensating* action to undo it if a
later step fails — e.g. "reserve inventory" pairs with "release
inventory" as its rollback. The tradeoff versus a monolith's transaction
is real complexity in exchange for independent service ownership.

### What does an API gateway actually do in a microservices setup?
A single entry point in front of many backend services, handling the
concerns that would otherwise be duplicated in every service: routing
requests to the right backend, authentication/rate-limiting at the edge,
request/response transformation, and often aggregating multiple backend
calls into one response for the client. It's also the natural place to
put cross-cutting observability (logging, metrics) without instrumenting
every service separately.
