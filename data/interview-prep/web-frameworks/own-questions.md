# Web Frameworks — additional possible questions

Supplementary to qa-bank.md.

### What's the difference between a path parameter and a query parameter in FastAPI?
A path parameter is part of the URL structure itself (`/users/{user_id}`)
and identifies a specific resource — it's required by definition. A query
parameter comes after `?` (`/users?active=true`) and is for optional
filtering, sorting, or pagination. FastAPI infers which is which from
whether the name appears in the route's path string.

### How do you handle authentication in a FastAPI (or similar) app?
Most commonly OAuth2 with JWT bearer tokens: a login endpoint issues a
signed token, and protected routes depend on a function that decodes and
validates that token (FastAPI's dependency-injection system makes this
clean — `Depends(get_current_user)` on any route that needs it). Sessions
with server-side state are the alternative, but are less common for an
API consumed by multiple clients since they need sticky sessions or a
shared session store.

### What is CORS, and why does a browser block a request without it?
Cross-Origin Resource Sharing — a browser security mechanism that blocks
a web page from making requests to a different origin (domain/port/scheme)
than the one it was served from, unless the server explicitly allows it
via `Access-Control-Allow-Origin` and related headers. In a Python backend
this is usually one middleware line (`CORSMiddleware` in FastAPI,
`django-cors-headers` in Django) — the mistake to avoid is wildcarding it
open (`allow_origins=["*"]`) in anything handling authenticated requests.

### What's middleware, and what's a concrete use case?
Code that runs on every request/response passing through the app, before
it reaches your route handler or after it leaves. Common real uses:
logging/request-id injection, auth-token verification, gzip compression,
and timing/metrics collection — anything that's genuinely cross-cutting
rather than specific to one endpoint.

### How would you structure a growing FastAPI project?
Split by domain, not by technical layer: a `routers/` package with one
file per resource (users, orders, ...), each importing its own
`schemas.py` (Pydantic models) and depending on shared `dependencies.py`
for things like DB sessions and the current-user check. A single flat
`main.py` with every route in it is fine at a handful of endpoints and
becomes genuinely painful well before 50.
