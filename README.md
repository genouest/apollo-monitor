# Apollo monitor

A simple app to regularly run queries on an Apollo database and inject results into an influxdb database.

## Configuring

The following options are available:

```
DELAY=1440  # Delay in minutes between each call (script written to collect data only once per day, you'll get duplicate values in influx db if you run it more frequently)
DB_STRING=postgresql://postgres:password@apollo-db/postgres  # Connection string to the Apollo SQL db
INFLUX_HOST=influx  # Host to connect to influxdb
INFLUX_PORT=8086  # Port to connect to influxdb
INFLUX_DB=apollo  # Name of the influxdb db (created if not found)
INSTANCE_NAME=server1  # Shortname of the apollo instance
OPTIONS=  # Add "-d" to enable dry-run mode, and/or "--suffix @example.org" to remove suffix from usernames
```

Checkout [docker-compose.prod.yml](./docker-compose.prod.yml) for an example.

A preconfigured Grafana dashboard is available in [./grafana/](./grafana/), feel free to adapt/adopts as needed.

## Loading old data

You can load old data by running this while the container is running (to load from 2015 to 2021 in this example):

```
docker-compose exec apollo-monitor bash
python /apollo-monitor/monitor.py "$DB_STRING" "$INFLUX_HOST" "$INFLUX_PORT" "$INFLUX_DB" "$INSTANCE_NAME" $OPTIONS --from-date 20170101 --to-date 20210101
```

Note that the old total numbers of organisms and users are not kept in Apollo database, so their values will not be loaded into influxdb for past dates.
