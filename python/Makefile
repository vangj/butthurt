.PHONY: all clean generate copy

all: clean generate copy

clean:
	rm -f blank_form.pdf blank_form.csv

generate:
	python generate_form.py

copy:
	cp -f blank_form.pdf ../www/pdf/blank_form.pdf