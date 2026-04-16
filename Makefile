.PHONY: test build clean install-dev

test:
	python -m pytest

build:
	python -m build

install-dev:
	python -m pip install -e '.[dev]'

clean:
	rm -rf build dist .pytest_cache src/*.egg-info src/codex_hotswap.egg-info
