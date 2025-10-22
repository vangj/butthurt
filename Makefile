.PHONY: all rebuild clean

all: clean build

build:
	@$(MAKE) -C python all
	npm run build:radio-map
	npm run build

clean:
	@$(MAKE) -C python clean
	rm -fr www-optimized
	rm -f www/js/radio-on-values.js
