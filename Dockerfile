# vim: set ft=conf
FROM python:3.9

RUN echo "US/Central" > /etc/timezone
RUN dpkg-reconfigure -f noninteractive tzdata

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONPATH /app:/app/coda

RUN mkdir /app
WORKDIR /app

RUN apt-get update -qq && apt-get install -y default-mysql-client netcat-openbsd

ADD requirements.txt /app/
RUN pip install -r requirements.txt

ADD wait-for-mysqld.sh /wait-for-mysqld.sh
ADD appstart.sh /appstart.sh
