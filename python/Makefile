.PHONY: all clean generate copy

all: clean generate copy

clean:
	rm -f blank_form*.pdf blank_form*.csv

generate:
	python generate_form.py -l all

copy:
	cp -f blank_form_*.pdf ../www/pdf/