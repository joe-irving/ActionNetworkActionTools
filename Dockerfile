FROM python:3.8.16-slim-buster

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
RUN pip install pipenv
COPY ./Pipfile /app/Pipfile
RUN pipenv install

COPY . /app/