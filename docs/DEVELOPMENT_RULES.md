# Development Rules

## General

One responsibility per class.

One purpose per module.

No business logic inside engine.py.

No business logic inside __init__.py.

All new functionality must have tests.

Every sprint ends with:

- pytest
- python -m atlas.core.engine
- git commit
- git push