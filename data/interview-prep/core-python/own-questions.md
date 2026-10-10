# Core Python — additional possible questions

Supplementary to qa-bank.md: questions a Python backend interview could
reasonably ask that the sourced bank doesn't cover, with answers written in
the same style.

### What's the difference between `*args` and `**kwargs`?
`*args` collects extra positional arguments into a tuple; `**kwargs`
collects extra keyword arguments into a dict. Both let a function accept a
variable, unknown-in-advance number of arguments, and both are purely a
calling-convention feature — nothing stops you from naming them something
else, `*args`/`**kwargs` is just the near-universal convention.

### How does Python's garbage collection actually work?
CPython uses two mechanisms together: reference counting (an object is
freed the instant its refcount hits zero) handles most cases immediately
and deterministically, and a separate generational cycle collector
periodically scans for reference cycles (objects that reference each
other and would otherwise never hit zero, e.g. two objects pointing at
each other) and collects those. Most Python code never needs to think
about this; it matters when you see memory grow despite objects going out
of scope — usually a cycle involving `__del__` or closures holding onto
large objects.

### What is the mutable default argument pitfall?
```python
def add_item(item, items=[]):   # BUG: the list is created ONCE at def time
    items.append(item)
    return items
```
The default list is created once when the function is defined, not on
every call, so it's silently shared and mutated across calls. The fix is
`items=None` with `items = items if items is not None else []` inside the
function body.

### `@staticmethod` vs `@classmethod` vs a regular instance method — when do you use each?
An instance method takes `self` and operates on a specific object's state.
A `@classmethod` takes `cls` instead and operates on the class itself —
common for alternative constructors (`from_dict`, `from_json`). A
`@staticmethod` takes neither — it's just a function namespaced inside the
class for organizational reasons, with no access to instance or class
state at all.

### What is a descriptor, and where have you actually seen one?
A descriptor is an object that customizes attribute access by implementing
`__get__`/`__set__`/`__delete__`. Python's own `property` is the most
common descriptor anyone uses without necessarily naming it that way;
ORMs (Django's model fields, SQLAlchemy's columns) and Pydantic's field
validation are built on the same mechanism under the hood.

### What is monkey-patching, and when (if ever) is it reasonable?
Replacing or extending a module/class's behavior at runtime, from outside
its own definition — e.g. reassigning `SomeClass.method = new_function`.
It's occasionally reasonable in tests (patching a dependency with
`unittest.mock.patch`) but risky in production code, since it makes
behavior depend on import order and is invisible to anyone reading the
original class definition.
