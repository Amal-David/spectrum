.PHONY: bootstrap demo dev

bootstrap:
	uv venv --python 3.11
	. .venv/bin/activate && uv pip install -e ".[server,audio,demo,dev,providers]"
	pnpm install

demo:
	uv run spectrum demo

dev:
	./scripts/dev.sh
