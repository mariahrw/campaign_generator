"""Rich console helpers for styled pipeline progress output."""

from contextlib import contextmanager

from rich.console import Console

console = Console()


@contextmanager
def step(description: str, indent: int = 0):
    """Shows a spinner for the duration of a pipeline stage, then a green checkmark line."""
    prefix = "  " * indent
    with console.status(f"[cyan]{prefix}{description}...[/cyan]", spinner="dots"):
        yield
    console.print(f"{prefix}[green]✓[/green] {description}")


def header(text: str, indent: int = 0):
    """Prints a plain (non-checkmarked) grouping line, e.g. a product or layout name."""
    console.print(f"\n{'  ' * indent}[bold]{text}[/bold]")


def warning(headline: str, detail: str = "", indent: int = 0, severe: bool = False):
    """Prints a warning line, bold red with a leading blank line when severe (e.g. a skipped product) instead of plain yellow."""
    prefix = "  " * indent
    style = "bold red" if severe else "yellow"
    icon = "✗" if severe else "!"
    lead = "\n" if severe else ""
    suffix = f" - {detail}" if detail else ""
    console.print(f"{lead}{prefix}[{style}]{icon} {headline}[/{style}]{suffix}")
