.PHONY: help

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: servdocs
servdocs: ## serve out the mkdocs documentation
	poetry run mkdocs serve

.PHONY: docs-serve
docs-serve: ## serve out the mkdocs documentation
	poetry run mkdocs serve

.PHONY: docs
docs: ## generate MkDocs HTML documentation, including API docs
	poetry run mkdocs build
	@echo docs generated into site directory

.PHONY: test
test: ## run tests quickly with the default Python
	poetry run pytest # --block-network

.PHONY: lint
lint: ## check style etc with pre-commit
	poetry run pre-commit run -a

# end
