"""
Structural tests that enforce layering rules and code quality invariants.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent
TICKET_REPO_FILE = APP_ROOT / "repositories" / "ticket.py"

# Layer ordering: lower layers must not import from higher layers
LAYER_ORDER = ["routers", "services", "repositories"]

# Map of layer -> set of layers it must NOT import from
FORBIDDEN_IMPORTS: dict[str, set[str]] = {}
for i, layer in enumerate(LAYER_ORDER):
    # Each layer cannot import from layers above it
    FORBIDDEN_IMPORTS[layer] = set(LAYER_ORDER[i + 1 :])


def _get_python_files(directory: Path) -> list[Path]:
    """Get all .py files in a directory recursively."""
    return list(directory.rglob("*.py"))


def _get_imports(filepath: Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _layer_of_import(module: str) -> str | None:
    """Return the layer name if the import is from src.app.<layer>, else None."""
    if not module.startswith("src.app."):
        return None
    parts = module.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def _get_function_defs(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return all (async) function definitions in a module."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _calls_select_on_tickets(node: ast.AST) -> bool:
    """True if this AST node contains a `select(Ticket)` or
    `select(tickets)`-style SQLAlchemy call."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            func_name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if func_name == "select":
                for arg in sub.args:
                    arg_name = getattr(arg, "id", None) or getattr(arg, "attr", None)
                    if arg_name in ("Ticket", "tickets"):
                        return True
    return False


def _has_account_id_filter(node: ast.AST) -> bool:
    """True if this AST node contains a `.where(...)` or `.filter(...)`
    call whose arguments reference `account_id` anywhere in the expression."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            method_name = getattr(func, "attr", None)
            if method_name in ("where", "filter"):
                # Reconstruct the filter expression as source and check for
                # the literal column reference. unparse is the simplest
                # reliable way to inspect arbitrary comparison shapes
                # (Ticket.account_id == x, tickets.c.account_id == x, etc.)
                for arg in sub.args:
                    if "account_id" in ast.unparse(arg):
                        return True
    return False


def test_no_backward_imports():
    """Verify no layer imports from a higher layer."""
    violations = []
    for layer in LAYER_ORDER:
        layer_dir = APP_ROOT / layer
        if not layer_dir.exists():
            continue
        for pyfile in _get_python_files(layer_dir):
            for imp in _get_imports(pyfile):
                imported_layer = _layer_of_import(imp)
                if imported_layer and imported_layer in FORBIDDEN_IMPORTS[layer]:
                    rel = pyfile.relative_to(APP_ROOT.parent)
                    violations.append(
                        f"{rel}: {layer}/ imports from {imported_layer}/ ({imp})"
                    )
    assert violations == [], "Backward import violations:\n" + "\n".join(violations)


def test_file_size_limits():
    """Verify no Python file exceeds 300 lines."""
    violations = []
    for pyfile in _get_python_files(APP_ROOT):
        line_count = len(pyfile.read_text().splitlines())
        if line_count > 300:
            rel = pyfile.relative_to(APP_ROOT.parent)
            violations.append(f"{rel}: {line_count} lines (max 300)")
    assert violations == [], "File size violations:\n" + "\n".join(violations)


def test_all_layers_exist():
    """Verify all expected layer directories exist."""
    for layer in LAYER_ORDER:
        layer_dir = APP_ROOT / layer
        assert layer_dir.exists(), f"Missing layer directory: src/app/{layer}/"
        init_file = layer_dir / "__init__.py"
        assert init_file.exists(), f"Missing __init__.py in src/app/{layer}/"


def test_ticket_queries_always_filter_by_account_id():
    """
    Every function in repositories/ticket.py that selects from the Ticket
    table must check always filter by account ID.
    """
    assert TICKET_REPO_FILE.exists(), (
        f"{TICKET_REPO_FILE} not found — per CONVENTIONS.md, all ticket "
        "queries must live in repositories/ticket.py"
    )

    tree = ast.parse(TICKET_REPO_FILE.read_text())
    violations = []

    for func in _get_function_defs(tree):
        if _calls_select_on_tickets(func) and not _has_account_id_filter(func):
            violations.append(
                f"{TICKET_REPO_FILE.name}:{func.lineno} "
                f"'{func.name}' selects from Ticket without an "
                f"account_id filter"
            )

    assert violations == [], (
        "Unscoped ticket query violations (ARCHITECTURE.md §6.3/§10.1):\n"
        + "\n".join(violations)
    )
