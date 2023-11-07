FROM python:3.6

LABEL maintainer "DataMade <info@datamade.us>"

RUN apt-get update && \
	apt-get install -y --no-install-recommends postgresql-client locales && \
	rm -rf /var/lib/apt/lists/* && \
	sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG en_US.UTF-8
ENV LC_NUMERIC en_US.UTF-8

RUN mkdir /app
WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV DJANGO_SECRET_KEY 'foobar'
ENV DJANGO_FLUSH_CACHE_KEY 'foobar'
ENV DJANGO_DEBUG 'False'

RUN python manage.py collectstatic --noinput
