# Databases interview questions

Sourced from a general Python backend developer Q&A bank, organized by seniority level.


## Junior

### What is a SQL (Structured Query Language) injection and how do you prevent it?
SQL (Structured Query Language) injection is an attack where malicious SQL statements are inserted into entry fields. Prevent it by using parameterized queries or an ORM (Object-Relational Mapping).

### What is the difference between INNER JOIN and LEFT JOIN?
INNER JOIN returns only the rows where there is a match in both tables. LEFT JOIN returns all rows from the left table, and the matched rows from the right table, with NULL for unmatched rows on the right.

### What is a Primary Key?
A Primary Key is a column or a set of columns that uniquely identifies each row in a database table. It cannot contain NULL values.

### What is a Foreign Key?
A Foreign Key is a column or group of columns in a relational database table that provides a link between data in two tables. It acts as a cross-reference between tables because it references the primary key of another table.


## Middle

### What are the key differences between PostgreSQL and a data warehouse like Snowflake?
PostgreSQL is an OLTP (Online Transaction Processing) database optimized for fast, transactional row-based inserts and updates. Snowflake is an OLAP (Online Analytical Processing) columnar data warehouse optimized for complex analytical queries over massive datasets.

### What are database indexes and how do they work?
Indexes are data structures (commonly B-Trees) that improve the speed of data retrieval operations on a database table at the cost of additional storage and decreased write performance. They work like an index in a book.

### Explain ACID (Atomicity, Consistency, Isolation, Durability) properties.
ACID (Atomicity, Consistency, Isolation, Durability) ensures reliable database transactions. Atomicity guarantees all-or-nothing execution; Consistency ensures database rules are maintained; Isolation handles concurrent transaction visibility; Durability guarantees committed data survives system failures.

### How do you handle parsing large XML (eXtensible Markup Language) or CSV (Comma-Separated Values) files before inserting them into a DB (Database)?
For XML (eXtensible Markup Language), use iterative parsers like lxml or xml.etree.ElementTree.iterparse to avoid loading the whole DOM (Document Object Model) into memory. For CSV (Comma-Separated Values), chunking via pandas.read_csv(chunksize=X) or using the standard csv library sequentially ensures memory limits aren't breached.


## Senior

### Explain MVCC (Multi-Version Concurrency Control) in PostgreSQL.
MVCC (Multi-Version Concurrency Control) allows concurrent access without locking. Each transaction sees a snapshot of data. Updates create a new version of the row, while the old one is kept for concurrent transactions until cleaned up by the VACUUM process.

### When and why would you use table partitioning?
Partitioning splits large tables into smaller, more manageable physical pieces based on a key (like date). It improves query performance (by skipping irrelevant partitions), speeds up bulk deletes (dropping partitions), and improves index efficiency.

### Why use PgBouncer in front of PostgreSQL?
PostgreSQL handles connections by creating a new OS (Operating System) process for each connection, which consumes high memory. PgBouncer acts as a connection pooler, maintaining a pool of database connections and multiplexing lightweight client connections onto them.

### How do you manage complex data migrations from a relational DB (Database) to a data warehouse like Snowflake?
Complex migrations require setting up ELT (Extract, Load, Transform) pipelines using tools like dbt (data build tool), Airflow, or Databricks. Data is extracted via CDC (Change Data Capture) or batch jobs, loaded into raw staging tables in Snowflake, and then transformed using SQL (Structured Query Language) within the warehouse to optimize for columnar analytics.
