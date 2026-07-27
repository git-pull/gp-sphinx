"""Policy tests for the docstrings the API reference is generated from.

Sibling to :mod:`tests.docs.test_docs_policy`, which polices hand-authored
pages. This module polices the Python source those pages render from.
"""

from __future__ import annotations

import ast
import pathlib
import typing as t

import pytest

_PACKAGES = pathlib.Path(__file__).resolve().parents[2] / "packages"
_NUMPY_SECTIONS = frozenset(
    {
        "Examples",
        "Notes",
        "Parameters",
        "Raises",
        "References",
        "Returns",
        "See Also",
        "Yields",
    }
)


class ShapeClass(t.NamedTuple):
    """A class whose fields autodoc renders one description each for.

    Attributes
    ----------
    test_id : str
        Short identifier used as the pytest parameter id.
    path : pathlib.Path
        File the class is declared in.
    name : str
        Class name.
    undescribed : tuple[str, ...]
        Public fields carrying no description in any supported style.
    """

    test_id: str
    path: pathlib.Path
    name: str
    undescribed: tuple[str, ...]


def _attributes_section(docstring: str | None) -> frozenset[str]:
    r"""Return the names a NumPy ``Attributes`` section describes.

    Parameters
    ----------
    docstring : str | None
        Class docstring, already dedented by :func:`ast.get_docstring`.

    Returns
    -------
    frozenset[str]
        Names carried by entries of the ``Attributes`` section.

    Examples
    --------
    >>> section = "Summary.\n\nAttributes\n----------\nx : int\n    Offset."
    >>> _attributes_section(section)
    frozenset({'x'})

    >>> _attributes_section("Summary.")
    frozenset()
    """
    if not docstring:
        return frozenset()
    lines = docstring.splitlines()
    described: set[str] = set()
    inside = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "Attributes":
            following = lines[index + 1].strip() if index + 1 < len(lines) else ""
            inside = bool(following) and set(following) == {"-"}
            continue
        if not inside:
            continue
        if stripped in _NUMPY_SECTIONS:
            break
        if " : " in stripped:
            described.add(stripped.split(" : ")[0].strip())
    return frozenset(described)


def _is_shape(node: ast.ClassDef) -> bool:
    """Return whether *node* declares a shape autodoc renders fields for.

    Parameters
    ----------
    node : ast.ClassDef
        Class definition under consideration.

    Returns
    -------
    bool
        Whether the class is a NamedTuple, TypedDict, dataclass, or Enum.

    Examples
    --------
    >>> _is_shape(ast.parse("class A(t.NamedTuple): pass").body[0])
    True

    >>> _is_shape(ast.parse("class A: pass").body[0])
    False
    """
    bases = " ".join(ast.unparse(base) for base in node.bases)
    decorators = " ".join(ast.unparse(deco) for deco in node.decorator_list)
    return "dataclass" in decorators or any(
        shape in bases for shape in ("NamedTuple", "TypedDict", "Enum")
    )


def _undescribed_fields(node: ast.ClassDef, source_lines: list[str]) -> tuple[str, ...]:
    r"""Return public fields *node* declares with no description anywhere.

    Three styles count, because autodoc honors all three and the workspace
    uses more than one: a NumPy ``Attributes`` entry, a PEP 224 string
    literal after the assignment, and a ``#:`` comment above it.

    Parameters
    ----------
    node : ast.ClassDef
        Class definition under consideration.
    source_lines : list[str]
        Lines of the file the class is declared in.

    Returns
    -------
    tuple[str, ...]
        Field names carrying no description, in declaration order.

    Examples
    --------
    >>> source = "class A:\n    x: int\n    y: int\n    #: Doc.\n    z: int\n"
    >>> _undescribed_fields(ast.parse(source).body[0], source.splitlines())
    ('x', 'y')
    """
    described = _attributes_section(ast.get_docstring(node))
    undescribed: list[str] = []
    for index, statement in enumerate(node.body):
        if isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            names = [statement.target.id]
        elif isinstance(statement, ast.Assign):
            names = [
                target.id
                for target in statement.targets
                if isinstance(target, ast.Name)
            ]
        else:
            continue

        following = node.body[index + 1] if index + 1 < len(node.body) else None
        has_attribute_docstring = (
            isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        )
        above = statement.lineno - 2
        has_comment = above >= 0 and source_lines[above].strip().startswith("#:")

        for name in names:
            if name.startswith("_") or name in described:
                continue
            if has_attribute_docstring or has_comment:
                continue
            undescribed.append(name)
    return tuple(undescribed)


def _shape_classes() -> list[ShapeClass]:
    """Return every public shape class declared under ``packages/``."""
    found: list[ShapeClass] = []
    for path in sorted(_PACKAGES.rglob("*.py")):
        if "tests" in path.parts:
            continue
        source = path.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:  # pragma: no cover - a package that cannot parse
            continue
        source_lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
                continue
            if not _is_shape(node):
                continue
            found.append(
                ShapeClass(
                    test_id=f"{path.stem}.{node.name}",
                    path=path,
                    name=node.name,
                    undescribed=_undescribed_fields(node, source_lines),
                )
            )
    return found


_SHAPE_CLASSES = _shape_classes()


def test_shape_classes_are_discovered() -> None:
    """The walk finds the workspace's shape classes rather than nothing."""
    assert len(_SHAPE_CLASSES) > 20


@pytest.mark.parametrize(
    "shape",
    _SHAPE_CLASSES,
    ids=[shape.test_id for shape in _SHAPE_CLASSES],
)
def test_every_shape_field_is_described(shape: ShapeClass) -> None:
    """Autodoc renders one entry per field, so every field needs prose.

    A field nobody describes reaches the API reference as a bare name, and
    a class variable nobody describes is withheld from it entirely. Either
    way the reader is worse off than if the class had not been documented
    at all.
    """
    relative = shape.path.relative_to(_PACKAGES.parent)
    assert not shape.undescribed, (
        f"{relative}:{shape.name} declares fields nothing describes: "
        f"{', '.join(shape.undescribed)}. Describe each in the class "
        f"docstring's Attributes section, in a docstring under the "
        f"assignment, or in a #: comment above it."
    )
