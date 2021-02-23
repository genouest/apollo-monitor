#!/bin/sh

while true
do
  python /apollo-monitor/monitor.py "$DB_STRING" "$INFLUX_HOST" "$INFLUX_PORT" "$INFLUX_DB" "$INSTANCE_NAME" $OPTIONS
  sleep $((60*$DELAY))
done
