# Core Python interview questions

Sourced from a general Python backend developer Q&A bank, organized by seniority level.


## Junior

### What is the difference between a list and a tuple?
Lists are mutable, meaning they can be changed after creation. Tuples are immutable and cannot be changed. Tuples are generally faster and can be used as dictionary keys.

### Explain the concept of PEP (Python Enhancement Proposal) 8.
PEP (Python Enhancement Proposal) 8 is the style guide for Python code, providing conventions for formatting, naming, and structuring code to maximize readability.

### What are list comprehensions?
List comprehensions provide a concise way to create lists based on existing lists or iterables, combining a for-loop and a conditional statement into a single line.

### What is the difference between deep and shallow copy?
A shallow copy creates a new object but inserts references into it to the objects found in the original. A deep copy creates a new object and recursively adds copies of nested objects found in the original.

### How does exception handling work in Python?
Exception handling uses try, except, else, and finally blocks. Code that might raise an exception goes in the try block, error handling in the except block, code that runs if no exception occurs in the else block, and cleanup code in the finally block.

### What is the purpose of the 'self' keyword in classes?
'self' represents the instance of the class. By using the 'self' keyword, we can access the attributes and methods of the class in Python. It binds the attributes with the given arguments.

### What are Python modules and packages?
A module is a single Python file containing variables, functions, and classes. A package is a directory of Python modules containing an __init__.py file, allowing for hierarchical structuring of the module namespace.

### Explain the difference between == and 'is'.
The == operator compares the values of both operands and checks for value equality. The 'is' operator checks whether both operands refer to the exact same object in memory (identity).


## Middle

### How does Python's asyncio work and what is the event loop?
Asyncio uses an event loop to run asynchronous tasks and callbacks, perform network I/O (Input/Output), and run subprocesses. It allows single-threaded concurrent code using coroutines via async/await syntax.

### What are decorators in Python and how do you create one?
Decorators are a design pattern that allows you to modify the functionality of a function or class by wrapping it in another function. They are created using the @ symbol above the function definition.

### Explain the GIL (Global Interpreter Lock).
The GIL (Global Interpreter Lock) is a mutex in CPython that allows only one thread to execute Python bytecode at a time. This prevents true parallelism for CPU-bound tasks in multi-threaded applications, though it doesn't heavily impact I/O-bound tasks.

### What are magic methods (dunder methods)?
Magic methods are special methods with double underscores at the beginning and end (e.g., __init__, __str__). They allow developers to define behavior for built-in operations like addition, string representation, or instantiation.

### What is Pydantic and how is it used?
Pydantic is a data validation and settings management library using Python type annotations. It enforces type hints at runtime and provides user-friendly errors, heavily used in modern frameworks like FastAPI.

### How do generators differ from standard functions?
Standard functions compute everything and return a single value or list, consuming memory for all items at once. Generators use the 'yield' keyword to return an iterator that generates one item at a time, making them highly memory-efficient for large datasets.

### What is the purpose of Pytest fixtures?
Pytest fixtures are functions that create data, test doubles, or initialize system state before a test runs, and tear them down afterward. They are highly reusable and help maintain clean, modular testing environments.

### Explain context managers and the 'with' statement.
Context managers handle the setup and teardown of resources (like opening and closing files or DB (Database) connections). The 'with' statement ensures that the __exit__ method is called to clean up resources automatically, even if an exception occurs.


## Senior

### How do metaclasses work in Python?
Metaclasses are 'classes of classes'. They define how a class behaves. A class is an instance of a metaclass (by default `type`). They allow interception of class creation, useful for ORMs (Object-Relational Mappings) or advanced framework abstractions.

### How do you profile a memory leak in a Python application?
You can use built-in tools like `tracemalloc` to trace memory allocation blocks, or `objgraph` to visualize reference cycles. Analyzing the GC (Garbage Collector) thresholds and tracking down uncollected objects held by global state or closures is standard practice.

### What is the difference between `__new__` and `__init__`?
`__new__` is a static method that creates and returns a new instance of the class. `__init__` is an instance method that initializes the already created object. `__new__` is primarily used when subclassing immutable types like tuples.

### Explain Python's Global Interpreter Lock (GIL) impact on Asyncio vs Threading.
Threading is limited by the GIL (Global Interpreter Lock) for CPU-bound tasks, meaning multiple threads cannot execute Python bytecode simultaneously. Asyncio runs in a single thread, bypassing the GIL (Global Interpreter Lock) contention entirely, making it highly efficient for managing thousands of concurrent I/O-bound (Input/Output) operations via event loops without OS (Operating System) context-switching overhead.
