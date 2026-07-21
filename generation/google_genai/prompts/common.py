"""Shared helpers for hydrating prompt templates safely."""

def _hydrate(template: str, **kwargs) -> str:
    """Fills a template's {placeholder} tokens, re-raising KeyError with the template and placeholder named."""
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise KeyError(f"Missing value for placeholder {e} while hydrating: {template[:60]}...") from e


def _with_constraints(template: str, constraints: list[str], **kwargs) -> str:
    """Hydrates the main template and each constraint line, then appends the constraints as a delimited list."""
    main = _hydrate(template, **kwargs)
    rules = "\n".join(f"- {_hydrate(c, **kwargs)}" for c in constraints)
    return f"{main}\n\nCONSTRAINTS (must follow exactly):\n{rules}"
