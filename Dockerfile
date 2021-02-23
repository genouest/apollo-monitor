FROM python:3.9-slim-buster

RUN mkdir /apollo-monitor

WORKDIR /apollo-monitor

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY monitor.py monitor.sh ./
RUN chmod +x monitor.sh

ENV DELAY=1440
ENV DB_STRING=postgresql://postgres:password@apollo-db/postgres
ENV INFLUX_HOST=influx
ENV INFLUX_PORT=8086
ENV INFLUX_DB=apollo
ENV INSTANCE_NAME=server1

ENTRYPOINT ["/apollo-monitor/monitor.sh"]
