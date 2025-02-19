FROM ghcr.io/hasura/ndc-python-lambda:v0.1.6

COPY requirements.txt /functions/

WORKDIR /functions
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt

COPY ./ /functions