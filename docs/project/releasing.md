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

5. Commit and tag with the repo-wide release format:

   ```console
   $ git commit -m 'build(release): Tag v0.0.1a1'
   ```

   ```console
   $ git tag v0.0.1a1
   ```

6. Push:

   ```console
   $ git push
   ```

   ```console
   $ git push --tags
   ```

7. GitHub Actions validates the shared version, builds all publishable
   packages, smoke-tests the built artifacts, and publishes them to PyPI

[uv]: https://github.com/astral-sh/uv
