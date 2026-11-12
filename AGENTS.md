# Project Guide: DSI Production

Course material for Deploying AI.

---

## Commands

- `uv` is the package manager. 
- The virtual environment is not the standard .venv, instead it is deploying-ai-env. 
- Use the `--active` flag if the environment is active.

```bash
uv run python -m pytest              # run full test suite
uv run python -m pytest tests/foo.py -v  # single file
uv run ruff check <files>            # lint
uv run pyrefly check <files>         # type check
```

Always use `uv run python` — bare `python` misses the project venv.

---

## Code Style

- No comments unless the WHY is non-obvious
- No unused imports — ruff F401 is enforced
- Docstrings: resolution-order lists and policy sections are welcome; avoid restating what the code already says


---

## Readme Files

Every subdirectory under `05_src/` has a `readme.md`. The top-level `src/readme.md` describes the overall system architecture and provides an end-to-end worked example. These files are a human-maintained source of truth for each module's design intent and public interface.

**Use them to inform your work.** Read a module's readme before exploring its source. When planning changes, check whether any readme content will become stale.

### What each readme must contain

- Description of the module's purpose and its main classes
- Public method and function signatures with parameter tables
- At least one fully runnable code example per major class

### Readme review is part of every PR

When a PR adds or changes a public class, method, field, or behaviour, the corresponding `readme.md` must be updated in the same PR. Check:

- New classes or functions are documented
- Changed field defaults, types, or constraints are reflected
- Changed validation rules or error messages are reflected
- Examples still run correctly against the updated code
- `src/readme.md` is still accurate if the module's role or main interfaces changed

Flag a missing or stale readme update the same way you flag a missing test.

