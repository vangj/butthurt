.PHONY: all clean generate generate-widget-data copy

all: clean generate copy

clean:
	rm -fr ./pdf
	rm -fr ./csv
	find . -type d -name "__pycache__" -exec rm -rf {} +

generate:
	python generate_form.py -l all --export-pdf --export-widget-data

generate-widget-data:
	python generate_form.py -l all --export-widget-data --no-export-pdf

copy:
	cp -f ./pdf/*.pdf ../www/pdf/
	cp -f ./pdf/blank_form_en.pdf ../www/pdf/blank_form.pdf
