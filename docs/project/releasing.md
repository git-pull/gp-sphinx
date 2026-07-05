# Releasing

## Version Policy

gp-sphinx is pre-1.0. Minor version bumps may include breaking changes.

All publishable workspace packages use a shared lockstep version. The
root `gp-sphinx-workspace` package stays a bootstrap package, but its
version should stay aligned with the publishable package set.

## Release Process

[uv] handles virtualenv creation, package requirements, versioning,
building, and publishing. There is no setup.py or requirements files.

1. Update `CHANGES` with release notes

2. Bump the shared version in the root `pyproject.toml` and in every
   package under `packages/*/pyproject.toml`

3. Update any exposed `__version__` values so they match the shared
   package version

4. Keep first-party workspace dependencies pinned exactly to the shared
   version

5. Commit with the repo-wide release format:

   ```console
   $ git commit -m 'Tag v0.0.1a7'
   ```

   The release manager creates and pushes the tag after review. Tags
   trigger publishing, so automated agents must leave tag creation to the
   maintainer running the release.

6. Push:

   ```console
   $ git push
   ```

7. GitHub Actions validates the shared version, builds all publishable
   packages, smoke-tests the built artifacts, and publishes them to PyPI

[uv]: https://github.com/astral-sh/uv
