# IoC / Service Registry

`app/core/registry.py` is a lightweight IoC container. Concrete services are registered **once** in `app/main.py` (composition root) against their Protocol interface. All other modules resolve via `registry.get()` — never import the concrete class.

```python
# main.py only
registry.register(ILogParserService, LogParserService())

# everywhere else
svc = registry.get(ILogParserService)
```

Service interfaces: `app/services/protocols.py`.
