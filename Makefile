.PHONY: all init test build clean lfs-pull

all: clean lfs-pull init build test

init:
	npm install

test:
	npm run test:e2e

build:
	@$(MAKE) -C python generate-widget-data
	npm run build:radio-map
	npm run build

clean:
	@$(MAKE) -C python clean
	rm -fr node_modules
	rm -fr www-optimized
	rm -f www/js/radio-on-values.js
	rm -fr test-results playwright-report .playwright

lfs-pull:
	git lfs fetch --all
	git lfs checkout