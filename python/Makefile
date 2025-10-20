.PHONY: clean
clean:
	rm -f blank_form.pdf blank_form.csv

.PHONY: generate
generate:
	python generate_form.py

.PHONY: copy
copy:
	cp -f blank_form.pdf ../www/blank_form.pdf

.PHONY: all
all: clean generate copy