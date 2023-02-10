FROM docker.io/python:3.11.2-alpine3.16 AS builder

RUN set -exu \
  && addgroup \
    --gid 1101 \
    fragminder \
  && adduser \
    --disabled-password \
    --gecos "" \
    --home /fragminder \
    --ingroup fragminder \
    --no-create-home \
    --uid 1101 \
    fragminder

USER fragminder

COPY --chown=fragminder . /fragminder

RUN set -exu \
  && cd /fragminder \
  && python3 setup.py bdist_wheel \
  && pip3 install --user /fragminder/dist/fragminder-0.0.1-py3-none-any.whl

WORKDIR /fragminder

CMD ["/fragminder/.local/bin/fragminder", "/fragminder/config.ini"]
