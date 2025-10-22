.PHONY: all rebuild clean lfs-pull

all: lfs-pull clean build

build:
	@$(MAKE) -C python all
	npm install
	npm run build:radio-map
	npm run build

clean:
	@$(MAKE) -C python clean
	rm -fr node_modules
	rm -fr www-optimized
	rm -f www/js/radio-on-values.js

lfs-pull:
	git lfs fetch --all
	git lfs checkout
