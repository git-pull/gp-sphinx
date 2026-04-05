from __future__ import annotations

from sphinx.ext.autodoc import Documenter


class SphinxConfigDocumenter(Documenter):
    objtype = "sphinxconfig"
    directivetype = "data"
    priority = 10 + Documenter.priority

    @classmethod
    def can_document_member(
        cls,
        member: object,  # object: stricter than Sphinx's Any; unused param
        membername: str,
        isattr: bool,
        parent: object,  # object: stricter than Sphinx's Any; unused param
    ) -> bool:
        return False

    def import_object(self, raiseerror: bool = False) -> bool:
        # We need access to the app to get config values.
        # In Sphinx Documenter, self.env.app is available.
        app = self.env.app
        if self.name in app.config.values:
            self.object = app.config.values[self.name]
            return True
        if raiseerror:
            msg = f"No sphinx config value found for {self.name}"
            raise ImportError(msg)
        return False

    def get_real_modname(self) -> str:
        return "sphinx.config"

    def get_doc(self) -> list[list[str]] | None:
        # Config values usually don't have docstrings attached to the values dict,
        # but we can format the default value and type.
        # Sphinx 8.x uses _Opt (class with .default/.rebuild/.valid_types attrs);
        # older Sphinx used a plain tuple. Support both.
        opt = self.object
        if isinstance(opt, tuple):
            default, rebuild, types = opt
        else:
            default = getattr(opt, "default", None)
            rebuild = getattr(opt, "rebuild", "")
            types = getattr(opt, "valid_types", ())
        doc = [f"Default: {default}", f"Rebuild: {rebuild}", f"Types: {types}"]
        return [doc]
