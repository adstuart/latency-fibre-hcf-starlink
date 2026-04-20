.PHONY: all model html clean

all: model html

model:
	.venv/bin/python model/latency_model.py

html:
	.venv/bin/python build_html.py

clean:
	rm -f data/results.json docs/index.html preview.png

setup:
	python3 -m venv .venv
	.venv/bin/pip install plotly jinja2 numpy
