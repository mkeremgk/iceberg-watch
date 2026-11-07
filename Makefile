PYTHON ?= python3
NODE ?= node

.PHONY: test test-web verify

test:
	$(PYTHON) main_project/submission/smoke_test.py

test-web:
	$(NODE) main_project/web_demo/test_routing.mjs
	$(NODE) main_project/web_demo/test_route_geometry.mjs

verify:
	$(PYTHON) main_project/submission/verify_package.py
