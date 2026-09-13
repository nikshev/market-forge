# The read API as PRD §6.2's `api` service.
#
# @trace: REQ-WP-064
#
# Two stages so the runtime image carries the dependency tree and not the tool
# that resolved it. `uv sync --frozen` is the same command `make install` runs,
# against the same lockfile, so an image cannot be built from a resolution a
# developer never saw.
#
# No credential is baked in. §34 keeps them in the environment, and
# `channelflow.api.main` refuses to start without the two it requires.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src

# The lockfile and the manifest first, so a change to source code does not
# re-resolve or re-download the dependency tree.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable --no-install-project

COPY src/ ./src/
# `--no-editable`: an editable install writes a path link to /src, and the
# runtime stage copies only the virtualenv. The image then builds, starts, and
# fails to import its own package -- which is why this is built and run in CI
# rather than reviewed as a file.
RUN uv sync --frozen --no-dev --no-editable


FROM python:3.12-slim AS runtime

# Not root. Nothing here writes to the image, and a process that cannot write to
# its own filesystem cannot be made to.
RUN useradd --create-home --uid 10001 channelflow

COPY --from=build --chown=channelflow:channelflow /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER channelflow
WORKDIR /home/channelflow

EXPOSE 8000

# A factory, not a module-level app: importing the module must not require the
# environment, so the test that checks the refusal can import the thing that
# refuses.
CMD ["uvicorn", "channelflow.api.main:application", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
