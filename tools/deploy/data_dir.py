"""Prepare and check the directory the stack keeps its data in.

# @trace: REQ-WP-065

A named volume is initialised by Docker, which copies the image's ownership onto
it. **A bind mount is not.** The host directory keeps the ownership it has, and
each image runs as a different user -- so on Linux a directory the service
cannot write is a container that fails to start, or one that starts and cannot
persist.

**This cannot be observed on a Mac.** Docker Desktop maps bind-mount access onto
the host user, so every service reports the directory writable whatever owns it:
measured, all five, including uid 65534 writing into a directory owned by
somebody else. The failure appears only on the server this exists to serve,
which is why the ownership is prepared rather than assumed and why the check
runs as the service's own user instead of as whoever ran the command.

Run through `make data-dirs`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: A throwaway image used only to create and own directories, so the same
#: command works on a Mac and on a server without either needing `sudo` or a
#: matching local user.
HELPER = "alpine:3.21"


@dataclass(frozen=True)
class Service:
    """One stateful service, and what its data directory must be.

    `uid` is the user the image runs as, read from the image rather than from
    documentation: `docker image inspect --format '{{.Config.User}}'`.
    """

    name: str
    #: The subdirectory under the data root.
    directory: str
    #: Where the container mounts it.
    mount: str
    uid: int
    gid: int


#: Measured on 2026-09-13 from the pinned images in `docker-compose.yml`.
#:
#: `postgres` and `minio` run as root and drop privileges themselves -- postgres
#: chowns its data directory in its entrypoint -- so their directories are left
#: to root, which is what those images expect to find.
SERVICES: tuple[Service, ...] = (
    Service("postgres", "postgres", "/var/lib/postgresql/data", 0, 0),
    Service("minio", "minio", "/data", 0, 0),
    Service("redpanda", "redpanda", "/var/lib/redpanda/data", 101, 101),
    Service("prometheus", "prometheus", "/prometheus", 65534, 65534),
    Service("grafana", "grafana", "/var/lib/grafana", 472, 472),
)


class NotWritable(RuntimeError):
    """A service's directory cannot be written by the user that service is."""


def _docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["docker", *arguments], capture_output=True, text=True, check=False
    )


def prepare(root: Path) -> list[str]:
    """Create each directory and give it to the user its service runs as."""
    made = []
    for service in SERVICES:
        target = root / service.directory
        target.mkdir(parents=True, exist_ok=True)
        result = _docker(
            "run",
            "--rm",
            "-v",
            f"{target.resolve()}:/target",
            HELPER,
            "chown",
            "-R",
            f"{service.uid}:{service.gid}",
            "/target",
        )
        if result.returncode != 0:
            raise RuntimeError(f"could not own {target} for {service.name}: {result.stderr}")
        made.append(f"{service.name}: {target} owned by {service.uid}:{service.gid}")
    return made


def verify(root: Path) -> list[str]:
    """Check each directory **as the user the service is**.

    Not as whoever ran this. A check that wrote as the operator would pass on
    every directory and prove nothing about the container, which is exactly the
    illusion Docker Desktop already provides.
    """
    problems = []
    for service in SERVICES:
        target = root / service.directory
        if not target.is_dir():
            problems.append(f"{service.name}: {target} does not exist")
            continue
        result = _docker(
            "run",
            "--rm",
            "--user",
            f"{service.uid}:{service.gid}",
            "-v",
            f"{target.resolve()}:/target",
            HELPER,
            "sh",
            "-c",
            "touch /target/.probe && rm /target/.probe",
        )
        if result.returncode != 0:
            problems.append(
                f"{service.name}: {target} is not writable by uid {service.uid}; "
                f"the container mounts it at {service.mount} and would fail to start"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="./data")
    parser.add_argument("--check-only", action="store_true")
    arguments = parser.parse_args(argv)

    root = Path(arguments.root)
    if not arguments.check_only:
        for line in prepare(root):
            print(f"  {line}")

    problems = verify(root)
    if problems:
        print("\nthese directories would stop the stack:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"\nall {len(SERVICES)} data directories are writable by the services that own them")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
