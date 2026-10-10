# Web Frameworks interview questions

Sourced from a general Python backend developer Q&A bank, organized by seniority level.


## Junior

### What is the difference between Flask and Django?
Django is a full-stack framework with a built-in ORM (Object-Relational Mapping), admin panel, and authentication. Flask is a microframework that provides the bare minimum, leaving the developer to choose their extensions.

### What is a route in a web framework?
A route is a mapping between an HTTP (Hypertext Transfer Protocol) URL (Uniform Resource Locator) and the specific Python function or method that should handle the request and return a response.

### How do you handle HTTP (Hypertext Transfer Protocol) methods like GET and POST in FastAPI?
In FastAPI, you use decorators like @app.get('/path') for GET requests and @app.post('/path') for POST requests to route the specific HTTP (Hypertext Transfer Protocol) methods to their respective handler functions.

### What is the purpose of a requirements.txt file?
It lists all the external libraries and their specific versions required to run a Python project, allowing other developers to install the exact same dependencies using pip install -r requirements.txt.


## Middle

### Explain Dependency Injection in FastAPI.
FastAPI uses a powerful dependency injection system allowing dependencies to be declared in route signatures. It executes them, caches results if needed, and passes the output to the endpoint, which is ideal for DB (Database) sessions or authentication extraction.

### How do you optimize Django ORM (Object-Relational Mapping) queries to prevent the N+1 problem?
By using `select_related()` for single-valued relationships (foreign keys) which performs a SQL (Structured Query Language) JOIN, and `prefetch_related()` for multi-valued relationships (many-to-many) which performs a separate lookup and joins in Python memory.

### Explain the difference between WSGI (Web Server Gateway Interface) and ASGI (Asynchronous Server Gateway Interface).
WSGI (Web Server Gateway Interface) is a standard for synchronous web apps, processing one request per thread at a time. ASGI (Asynchronous Server Gateway Interface) is its spiritual successor designed for asynchronous apps, allowing concurrent connection handling natively.

### How do you handle schema migrations in SQLAlchemy?
You typically use Alembic, a lightweight database migration tool for usage with the SQLAlchemy DB (Database) Toolkit. Alembic tracks changes to the SQLAlchemy models and generates migration scripts to upgrade or downgrade the database schema.


## Senior

### How do you handle background tasks in a high-traffic Python application?
By offloading them to an asynchronous task queue like Celery or RQ (Redis Queue), using a message broker like RabbitMQ or Redis. This prevents long-running tasks from blocking web request workers.

### How would you design a rate-limiting middleware?
I would implement a distributed counter using Redis and the Sliding Window or Token Bucket algorithm. The middleware would intercept the request, extract the IP (Internet Protocol) or user ID (Identifier), and check/increment the Redis key before passing the request to the application layer.

### How do you implement and version prompts in an LLM (Large Language Model) integrated backend?
Prompts should be treated as code. They can be stored in a dedicated configuration DB (Database) or managed via version control alongside the application code. Frameworks like LangChain allow abstraction, but managing template versions via Git or a specialized prompt registry ensures reproducibility and easy rollbacks.
