# vim: set ft=conf
FROM python:2.7

ENV PYTHONPATH=/app/coda
RUN apt-get update 
RUN apt-get update -qq && apt-get install -y \
    mysql-client

ADD requirements.txt /requirements.txt
RUN pip install --upgrade pip==1.5.6
RUN pip install -r /requirements.txt

RUN mkdir /app
WORKDIR /app
