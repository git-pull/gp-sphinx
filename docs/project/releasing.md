# Releasing

## Version Policy

gp-sphinx is pre-1.0. Minor version bumps may include breaking changes.

## Release Process

[uv] handles virtualenv creation, package requirements, versioning,
building, and publishing. There is no setup.py or requirements files.

1. Update `CHANGES` with release notes

2. Bump version in `src/gp_sphinx/__init__.py` and `pyproject.toml`

3. Commit and tag:

   ```console
   $ git commit -m 'build(gp_sphinx): Tag v0.0.1'
   ```

   ```console
   $ git tag v0.0.1
   ```

4. Push:

   ```console
   $ git push
   ```

   ```console
   $ git push --tags
   ```

[uv]: https://github.com/astral-sh/uv
