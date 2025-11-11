"""Utilities that adapt external artefacts to match Kai's conventions."""
from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional


@dataclass
class AdaptationPlan:
    """Represents the set of transformations that should be applied."""

    language: str = "typescript"
    normalize_indentation: bool = True
    trim_trailing_whitespace: bool = True
    ensure_newline_eof: bool = True


class Adapter:
    """Apply formatting and scaffolding rules to imported snippets."""

    def __init__(self, plan: Optional[AdaptationPlan] = None) -> None:
        self.plan = plan or AdaptationPlan()

    # ------------------------------------------------------------------
    def _trim_trailing_whitespace(self, text: str) -> str:
        return "\n".join(line.rstrip() for line in text.splitlines())

    def _ensure_newline(self, text: str) -> str:
        return text if text.endswith("\n") else text + "\n"

    # ------------------------------------------------------------------
    def normalise(self, text: str, indent: int = 2) -> str:
        """Apply the configured normalisation pipeline to ``text``."""

        result = text
        if self.plan.normalize_indentation:
            result = textwrap.dedent(result)
            indent_str = " " * indent
            result = "\n".join(
                indent_str + line if line and not line.startswith(indent_str) else line
                for line in result.splitlines()
            )
        if self.plan.trim_trailing_whitespace:
            result = self._trim_trailing_whitespace(result)
        if self.plan.ensure_newline_eof:
            result = self._ensure_newline(result)
        return result

    # ------------------------------------------------------------------
    def create_react_component(
        self,
        name: str,
        body: str,
        props_interface: Optional[str] = None,
        is_client_component: bool = False,
    ) -> str:
        """Return a ready-to-use React component template."""

        props_block = f"interface {name}Props {props_interface}\n\n" if props_interface else ""
        client_directive = "'use client';\n\n" if is_client_component else ""
        component = (
            f"{client_directive}{props_block}const {name}: React.FC"
            + (f"<{name}Props>" if props_interface else "")
            + " = () => {\n"
            + textwrap.indent(body.strip(), "    ")
            + "\n};\n\nexport default {name};\n"
        )
        return self.normalise(component)

    # ------------------------------------------------------------------
    def ensure_dependency_versions(
        self,
        package_json: Path,
        dependencies: Dict[str, str],
        section: str = "dependencies",
    ) -> Dict[str, str]:
        """Merge dependency requirements into ``package.json``.

        Returns the resulting dependency mapping so callers can inspect
        the diff without reopening the file.
        """

        data = json.loads(package_json.read_text())
        data.setdefault(section, {})
        for name, version in dependencies.items():
            current = data[section].get(name)
            if current != version:
                data[section][name] = version
        package_json.write_text(json.dumps(data, indent=2) + "\n")
        return dict(sorted(data[section].items()))

    # ------------------------------------------------------------------
    def apply_import_aliases(self, code: str, aliases: Dict[str, str]) -> str:
        """Rewrite bare module imports to use local alias paths."""

        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("import"):
                for old, new in aliases.items():
                    if f"'{old}'" in stripped or f'"{old}"' in stripped:
                        line = line.replace(f"'{old}'", f"'{new}'").replace(f'"{old}"', f'"{new}"')
            lines.append(line)
        result = "\n".join(lines)
        return self.normalise(result)

    # ------------------------------------------------------------------
    def adapt_markdown(self, markdown: str, badges: Optional[Iterable[str]] = None) -> str:
        """Prepare imported README files before storing them in the knowledge base."""

        processed = markdown.strip()
        if badges:
            badge_block = "\n".join(badges)
            processed = f"{badge_block}\n\n{processed}"
        return self.normalise(processed, indent=0)


__all__ = ["Adapter", "AdaptationPlan"]
