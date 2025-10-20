.PHONY: build clean

build:
	@echo "Building with uv..."
	uv sync
	uv run pyinstaller \
		--onedir \
		-w \
		-i res/icon.icns \
		--name Chanscrape \
		gui.py

clean:
	@echo "Cleaning up build artifacts..."
	rm -rf build dist *.spec .venv venv
