FROM ghcr.io/hasura/ndc-python-lambda:v{{VERSION}}

COPY requirements.txt /functions/

WORKDIR /functions
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install -r requirements.txt

COPY ./ /functions