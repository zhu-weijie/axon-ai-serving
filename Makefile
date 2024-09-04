format_all:
	@echo "Formatting all Python code with Black, excluding migrations, and other non-code files/directories..."
	@black . --exclude '/(migrations|venv|__pycache__|\.git|db.sqlite3)'

	@echo "Formatting all HTML files with djlint..."
	@if command -v djlint >/dev/null 2>&1; then \
		find . -name '*.html' -not -path "./venv/*" -exec djlint --reformat {} +; \
	else \
		echo "djlint is not installed. Skipping HTML formatting."; \
	fi

	@if command -v prettier >/dev/null 2>&1; then \
		echo "Formatting all CSS files with Prettier..."; \
		prettier --write "**/*.css"; \
	else \
		echo "Prettier is not installed. Skipping CSS formatting."; \
	fi

	@if command -v prettier >/dev/null 2>&1; then \
		echo "Formatting all Markdown files with Prettier..."; \
		prettier --write "**/*.md"; \
	else \
		echo "Prettier is not installed. Skipping Markdown formatting."; \
	fi

format:
	@echo "Formatting changed Python code with Black, excluding migrations, and other non-code files/directories..."
	@CHANGED_PY_FILES=$$(git diff --name-only --diff-filter=ACMRTUXB HEAD | grep -E '\.py$$' | grep -v 'venv/'); \
	if [ -n "$$CHANGED_PY_FILES" ]; then \
		echo "$$CHANGED_PY_FILES" | xargs black --exclude '/(migrations|venv|__pycache__|\.git|db.sqlite3)'; \
	else \
		echo "No Python files to format."; \
	fi

	@echo "Formatting changed HTML files with djlint..."
	@if command -v djlint >/dev/null 2>&1; then \
		CHANGED_HTML_FILES=$$(git diff --name-only --diff-filter=ACMRTUXB HEAD | grep -E '\.html$$' | grep -v 'venv/'); \
		if [ -n "$$CHANGED_HTML_FILES" ]; then \
			echo "$$CHANGED_HTML_FILES" | xargs djlint --reformat; \
		else \
			echo "No HTML files to format."; \
		fi \
	else \
		echo "djlint is not installed. Skipping HTML formatting."; \
	fi

	@if command -v prettier >/dev/null 2>&1; then \
		CHANGED_CSS_FILES=$$(git diff --name-only --diff-filter=ACMRTUXB HEAD | grep -E '\.css$$' | grep -v 'venv/'); \
		if [ -n "$$CHANGED_CSS_FILES" ]; then \
			echo "Formatting changed CSS files with Prettier..."; \
			echo "$$CHANGED_CSS_FILES" | xargs prettier --write; \
		else \
			echo "No CSS files to format."; \
		fi \
	else \
		echo "Prettier is not installed. Skipping CSS formatting."; \
	fi

	@if command -v prettier >/dev/null 2>&1; then \
		CHANGED_MD_FILES=$$(git diff --name-only --diff-filter=ACMRTUXB HEAD | grep -E '\.md$$' | grep -v 'venv/'); \
		if [ -n "$$CHANGED_MD_FILES" ]; then \
			echo "Formatting changed Markdown files with Prettier..."; \
			echo "$$CHANGED_MD_FILES" | xargs prettier --write; \
		else \
			echo "No Markdown files to format."; \
		fi \
	else \
		echo "Prettier is not installed. Skipping Markdown formatting."; \
	fi
