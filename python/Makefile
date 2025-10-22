.PHONY: all clean generate copy

all: clean generate copy

clean:
	rm -f ./pdf/*

generate:
	python generate_form.py -l all --export-widget-data

copy:
	cp -f ./pdf/*.pdf ../www/pdf/
	cp -f ./pdf/blank_form_en.pdf ../www/pdf/blank_form.pdf