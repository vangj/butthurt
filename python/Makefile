.PHONY: all clean generate copy

all: clean generate copy

clean:
	rm -f blank_form*.pdf blank_form*.csv

generate:
	python generate_form.py -l all

copy:
	cp -f ./pdf/*.pdf ../www/pdf/
	cp -f ./pdf/blank_form_en.pdf ../www/pdf/blank_form.pdf