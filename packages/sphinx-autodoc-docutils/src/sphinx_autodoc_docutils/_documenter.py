from __future__ import annotations

import inspect
import typing as t

from docutils.parsers.rst import directives, roles
from sphinx.ext.autodoc import Documenter


class DocutilsDocumenter(Documenter):
    objtype = "docutils"
    directivetype = "class"
    priority = 10 + Documenter.priority

    @classmethod
    def can_document_member(
        cls,
        member: object,
        membername: str,
        isattr: bool,
        parent: object,
    ) -> bool:
        return False

    def import_object(self, raiseerror: bool = False) -> bool:
        directive_registry = t.cast(
            dict[str, object], getattr(directives, "_directives", {})
        )
        role_registry = t.cast(dict[str, object], getattr(roles, "_roles", {}))
        if self.name in directive_registry:
            self.object = directive_registry[self.name]
            self.docutils_type = "directive"
            return True
        if self.name in role_registry:
            self.object = role_registry[self.name]
            self.docutils_type = "role"
            return True
        if raiseerror:
            raise ImportError(f"No docutils directive or role found for {self.name}")
        return False

    def get_real_modname(self) -> str:
        if hasattr(self.object, "__module__"):
            return t.cast(str, self.object.__module__)
        return type(self.object).__module__

    def get_doc(self) -> list[list[str]] | None:
        docstring = inspect.getdoc(self.object)
        if docstring:
            return [docstring.splitlines()]
        return []
