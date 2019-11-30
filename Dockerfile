FROM python:3.6.9

ADD . /work
WORKDIR /work


COPY requirements.txt /work/
RUN pip install -r requirements.txt
