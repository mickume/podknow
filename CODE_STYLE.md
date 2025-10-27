# PodKnow Code Style Guide

## String Formatting Standard (ISSUE-013)

**Date Implemented:** 2025-10-27

### Standard: Use F-Strings

PodKnow uses modern **f-strings** (PEP 498) for all string formatting in Python 3.6+.

### ✅ Preferred (F-Strings)

```python
# Simple variable substitution
name = "podcast"
message = f"Processing {name}"

# Expressions
count = 10
status = f"Found {count + 5} episodes"

# Multi-line
result = (
    f"Transcription complete for {podcast_title}. "
    f"Duration: {duration:.2f} seconds"
)

# Error messages
raise NetworkError(f"API request failed: {error}")
```

### ❌ Avoid (Old-Style Formatting)

```python
# Don't use .format() for immediate formatting
message = "Processing {}".format(name)

# Don't use % formatting
message = "Processing %s" % name

# Don't use string concatenation
message = "Processing " + name
```

### Exception: Template Substitution

Use `.format()` **only** when the template string needs to be stored or passed around:

```python
# ✅ Correct: Template stored separately
template = "Error {error_type}: {message}"
result = template.format(error_type="Network", message="Timeout")

# ✅ Correct: User-configurable templates
filename_template = config.get("filename_template")  # "{title}_{date}.md"
filename = filename_template.format(title=podcast, date=today)
```

See `podknow/services/config.py` for examples of legitimate template usage.

### Enforcement

String formatting standards are enforced via Ruff linting:

- **UP031**: Enforces format specifiers over % format
- **UP032**: Enforces f-strings over .format() calls
- **UP034**: Enforces f-strings over % formatting

Run linting:
```bash
ruff check podknow/
```

### Benefits

1. **Readability**: F-strings are more concise and readable
2. **Performance**: F-strings are faster than .format() and %
3. **Type Safety**: Better IDE support and type checking
4. **Consistency**: Single standard across the codebase

### Current Status

✅ **Verified 2025-10-27**: All 100+ files in `podknow/` use f-strings consistently.
- Only 2 legitimate `.format()` calls remain in `config.py` for template substitution
- Zero % formatting found
- Zero string concatenation for formatting

---

*This standard was established to resolve ISSUE-013 and improve code maintainability.*
