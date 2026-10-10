# Architecture interview questions

Sourced from a general Python backend developer Q&A bank, organized by seniority level.


## Middle

### What is the ELK (Elasticsearch, Logstash, Kibana) stack used for in backend architecture?
The ELK (Elasticsearch, Logstash, Kibana) stack is used for centralized logging. Logstash collects and processes logs via pipelines, Elasticsearch indexes them for fast full-text searching, and Kibana provides a dashboard for visual analysis.

### What is the difference between a Monolith and Microservices architecture?
A monolith bundles all application components into a single deployable unit, making it easier to test initially but harder to scale and maintain. Microservices separate the application into independent, loosely coupled services communicating via APIs (Application Programming Interfaces).

### Why use Docker in backend development?
Docker packages applications and their dependencies into standardized containers. This guarantees environmental consistency across local development, testing frameworks (like validating hardware setups), and production servers, completely eliminating 'it works on my machine' issues.


## Senior

### Design a RAG (Retrieval-Augmented Generation) system. What components are necessary?
A RAG (Retrieval-Augmented Generation) system needs an embedding model to convert text to vectors, a vector database (like Qdrant) for similarity search, an orchestration layer (like LangChain) to retrieve context, and an LLM (Large Language Model) to generate the response based on the prompt combined with the retrieved context.

### Explain the CAP (Consistency, Availability, Partition Tolerance) Theorem.
The CAP (Consistency, Availability, Partition Tolerance) Theorem states that a distributed data store can simultaneously provide at most two of the three guarantees: Consistency (every read receives the most recent write), Availability (every request receives a non-error response), and Partition Tolerance (the system continues operating despite network drops).

### How do you design a robust automated testing framework for hardware/firmware validation using Python?
You architect a modular, event-driven framework using Pytest. It should utilize asynchronous I/O (Input/Output) or multithreading to manage concurrent hardware serial connections, mock hardware states for unit tests, and integrate CI/CD (Continuous Integration / Continuous Deployment) pipelines that aggregate test metrics and logs into a centralized dashboard like the ELK (Elasticsearch, Logstash, Kibana) stack.
