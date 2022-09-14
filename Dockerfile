# To use (currently)
# $ docker build -t $NAME .
# $ docker run -it --name $NAME $NAME /bin/bash

FROM alpine:latest

ENV LSP_DIR=/opt/lsps

RUN \
    mkdir -p ${LSP_DIR} &&\
    apk add --update --no-cache python3 git bash &&\
    ln -sf /usr/bin/python3 /usr/bin/python &&\
    /usr/bin/python3 -m ensurepip &&\
    /usr/bin/pip3 install --no-cache --upgrade pip setuptools flask
