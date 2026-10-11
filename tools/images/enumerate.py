# @trace: REQ-INFRA-013
"""Which container images does the repository name? (REQ-INFRA-013)

Parsing, not running: the compose file (every profile, YAML anchors and `${VAR:-default}` resolved,
services with a `build:` skipped because they are tagged locally), the Dockerfiles (`FROM` and
`COPY --from`, stage names and `scratch` skipped, `ARG` defaults substituted as Docker does), and
the CI workflows (`services:` images and the image of each `docker run` command in a `run:` block).

**A reference the parser cannot turn into an image is reported, never dropped.** A variable with
no default, an `ARG` with none: silently skipping those is how a check goes green while the thing
it was written to watch is not being watched.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_SKIP_DIRS = {".git", "node_modules", ".venv", "data", ".mypy_cache", ".pytest_cache", "dist"}
_VARIABLE = re.compile(r"\$\{([A-Za-z_]\w*)(?::?-([^}]*))?\}|\$([A-Za-z_]\w*)")
#: `docker run` options that take a value as the next argument.
_VALUE_OPTIONS = {
    "-p", "--publish", "-e", "--env", "--name", "--network", "--net", "--entrypoint", "-v",
    "--volume", "--mount", "-u", "--user", "-w", "--workdir", "--platform", "--label", "-l",
    "--add-host", "--env-file", "--hostname", "-h", "--cpus", "-m", "--memory", "--restart",
    "--health-cmd", "--pull",
}  # fmt: skip


@dataclass(frozen=True)
class ImageRef:
    name: str
    tag: str | None
    digest: str | None
    where: str

    @property
    def reference(self) -> str:
        """Exactly what a registry is asked about: name, `:tag`, `@digest` as written."""
        return (
            self.name
            + (f":{self.tag}" if self.tag else "")
            + (f"@{self.digest}" if self.digest else "")
        )


@dataclass
class Enumeration:
    images: list[ImageRef] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def parse_reference(text: str, *, where: str) -> ImageRef:
    digest = None
    if "@" in text:
        text, digest = text.split("@", 1)
    colon = text.rfind(":")
    if colon > text.rfind("/"):
        return ImageRef(text[:colon], text[colon + 1 :], digest, where)
    return ImageRef(text, None, digest, where)


def _substitute(text: str, known: dict[str, str] | None = None) -> tuple[str, list[str]]:
    """Replace `${VAR:-default}` / `$VAR`; return the text and the names that had no value."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(3)
        default = match.group(2)
        if known and name in known:
            return known[name]
        if default is not None:
            return default
        missing.append(name)
        return match.group(0)

    return _VARIABLE.sub(replace, text), missing


def _add(found: Enumeration, text: str, *, where: str, known: dict[str, str] | None = None) -> None:
    resolved, missing = _substitute(text.strip(), known)
    if missing:
        found.unresolved.append(
            f"{where}: image {text.strip()!r} uses {', '.join(missing)} with no default"
        )
        return
    if resolved:
        found.images.append(parse_reference(resolved, where=where))


def _compose(root: Path, found: Enumeration) -> None:
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        path = root / name
        if not path.is_file():
            continue
        document: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
        for service, spec in (document.get("services") or {}).items():
            if not isinstance(spec, dict) or "build" in spec or "image" not in spec:
                continue  # built from this repository: tagged locally, never pulled
            _add(found, str(spec["image"]), where=f"{name} (service {service})")


def _dockerfiles(root: Path, found: Enumeration) -> None:
    for path in sorted(root.rglob("Dockerfile*")):
        if _SKIP_DIRS & set(path.relative_to(root).parts) or not path.is_file():
            continue
        rel = path.relative_to(root)
        args: dict[str, str] = {}
        stages: set[str] = set()
        for number, raw in enumerate(path.read_text().splitlines(), 1):
            line = raw.split("#", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
            if not line:
                continue
            where = f"{rel}:{number}"
            upper = line.upper()
            if upper.startswith("ARG "):
                declaration = line[4:].strip()
                if "=" in declaration:
                    key, _, value = declaration.partition("=")
                    args[key.strip()] = value.strip().strip("\"'")
            elif upper.startswith("FROM "):
                tokens = [t for t in line.split()[1:] if not t.startswith("--")]
                if not tokens:
                    continue
                image = tokens[0]
                names_an_earlier_stage = image.lower() in stages
                if len(tokens) >= 3 and tokens[1].upper() == "AS":
                    stages.add(
                        tokens[2].lower()
                    )  # registered after the check: a stage cannot start FROM itself
                if names_an_earlier_stage or image.lower() == "scratch":
                    continue
                _add(found, image, where=where, known=args)
            elif upper.startswith("COPY ") or upper.startswith("ADD "):
                match = re.search(r"--from=(\S+)", line)
                if match and not match.group(1).isdigit() and match.group(1).lower() not in stages:
                    _add(found, match.group(1), where=where, known=args)


def _docker_run_image(line: str) -> str | None:
    """The image of a `docker run ...` command line, or `None` if there is no such command."""
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError:
        return None
    for index in range(len(tokens) - 1):
        if tokens[index] == "docker" and tokens[index + 1] == "run":
            rest = tokens[index + 2 :]
            skip = False
            for token in rest:
                if skip:
                    skip = False
                    continue
                if token.startswith("-"):
                    skip = token in _VALUE_OPTIONS and "=" not in token
                    continue
                return token
    return None


def _built_tags(script: str) -> set[str]:
    """Tags a script gives to images it builds itself (`docker build -t NAME`): never pulled."""
    tags: set[str] = set()
    for line in re.sub(r"\\\n\s*", " ", script).splitlines():
        if "docker" not in line or "build" not in line:
            continue
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError:
            continue
        for index, token in enumerate(tokens):
            if token in {"-t", "--tag"} and index + 1 < len(tokens):
                tags.add(tokens[index + 1])
            elif token.startswith("--tag="):
                tags.add(token.split("=", 1)[1])
    return tags


def _workflows(root: Path, found: Enumeration) -> None:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return
    for path in sorted(list(directory.glob("*.yml")) + list(directory.glob("*.yaml"))):
        rel = path.relative_to(root)
        document: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
        for job_name, job in (document.get("jobs") or {}).items():
            steps = [s for s in ((job or {}).get("steps") or []) if isinstance(s, dict)]
            scripts = [s["run"] for s in steps if isinstance(s.get("run"), str)]
            built = set().union(*(_built_tags(script) for script in scripts)) if scripts else set()
            for service, spec in ((job or {}).get("services") or {}).items():
                if isinstance(spec, dict) and "image" in spec:
                    _add(
                        found,
                        str(spec["image"]),
                        where=f"{rel} (job {job_name}, service {service})",
                    )
            for step in steps:
                script = step.get("run")
                if not isinstance(script, str):
                    continue
                label = step.get("name") or "a run step"
                joined = re.sub(r"\\\n\s*", " ", script)
                for line in joined.splitlines():
                    if "docker" in line and "run" in line:
                        image = _docker_run_image(line)
                        if image and image not in built:
                            _add(found, image, where=f"{rel} (job {job_name}, step {label!r})")


def enumerate_images(root: Path) -> Enumeration:
    found = Enumeration()
    _compose(root, found)
    _dockerfiles(root, found)
    _workflows(root, found)
    return found
