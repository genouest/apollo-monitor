#!/usr/bin/env python

import click
import datetime

from influxdb import InfluxDBClient
from sqlalchemy import create_engine


class ApolloMonitor():

    db_string = None
    engine = None
    connection = None
    influx = None

    def __init__(self, db_string, influx_host, influx_port, influx_db, instance_name, suffix):
        self.db_string = db_string
        self.influx_host = influx_host
        self.influx_port = influx_port
        self.influx_db = influx_db
        self.instance_name = instance_name
        self.suffix = suffix

    def influx_client(self):
        if self.influx is None:
            self.influx = InfluxDBClient(host=self.influx_host, port=self.influx_port)

            # Check if db exists, create it if not
            dbs = self.influx.get_list_database()
            dbs = [x['name'] for x in dbs]
            if self.influx_db not in dbs:
                self.influx.create_database(self.influx_db)

            self.influx.switch_database(self.influx_db)

        return self.influx

    def connect(self):
        if self.connection is None:
            self.engine = create_engine(self.db_string)
            self.connection = self.engine.connect()

        return self.connection

    def get_organisms(self):

        con = self.connect()

        res = con.execute('SELECT id, common_name FROM organism')

        orgs = {}
        for x in res:
            orgs[x[0]] = {'common_name': x[1], 'slug': x[1].lower().replace(' ', '_').replace('.', '_')}

        return orgs

    def get_genes_by_org(self, day):

        con = self.connect()

        res = con.execute("""select o.common_name, count(f.id)
            from feature f, feature_location l, sequence s, organism o
            where class='org.bbop.apollo.Gene'
            and f.id = l.feature_id
            and l.sequence_id = s.id
            and s.organism_id = o.id
            and f.date_created <= '%s'::date
            group by o.id""" % day.strftime("%Y.%m.%d"))

        counts = {}
        for x in res:
            counts[x[0].lower().replace(' ', '_').replace('.', '_')] = x[1]

        return counts

    def get_users_by_org(self, day):

        con = self.connect()

        res = con.execute("""select o.common_name, count(distinct g.user_id)
            from feature f, feature_grails_user g, feature_location l, sequence s, organism o
            where class='org.bbop.apollo.Gene'
            and f.id = l.feature_id
            and l.sequence_id = s.id
            and s.organism_id = o.id
            and f.id = g.feature_owners_id
            and f.date_created <= '%s'::date
            group by o.id""" % day.strftime("%Y.%m.%d"))

        counts = {}
        for x in res:
            counts[x[0].lower().replace(' ', '_').replace('.', '_')] = x[1]

        return counts

    def get_users(self):

        con = self.connect()

        res = con.execute('SELECT id, username FROM grails_user')

        orgs = {}
        for x in res:
            if self.suffix and x[1].endswith(self.suffix):
                orgs[x[0]] = x[1][:-len(self.suffix)]
            else:
                orgs[x[0]] = x[1]

        return orgs

    def get_genes_by_users(self, day):

        con = self.connect()

        res = con.execute("""select u.username, count(f.id)
            from feature f, feature_grails_user g, grails_user u
            where class='org.bbop.apollo.Gene'
            and f.id = g.feature_owners_id
            and g.user_id = u.id
            and f.date_created <= '%s'::date
            group by u.username
            """ % day.strftime("%Y.%m.%d"))

        counts = {}
        for x in res:
            if self.suffix and x[0].endswith(self.suffix):
                counts[x[0][:-len(self.suffix)]] = x[1]
            else:
                counts[x[0]] = x[1]

        return counts

    def prepare_influx_points(self, measure, value, day):

        points = []
        points.append({
            "measurement": "apollo.%s" % (measure),
            "time": int(day.timestamp()) * 1000000000,
            "tags": {
                "instance": self.instance_name
            },
            "fields": {
                "value": value
            }
        })

        return points

    def prepare_influx_points_by_x(self, measure, value, by_x, day):

        points = []
        for elem in value:
            points.append({
                "measurement": "apollo.%s" % (measure),
                "time": int(day.timestamp()) * 1000000000,
                "tags": {
                    "instance": self.instance_name,
                    by_x: elem
                },
                "fields": {
                    "value": value[elem]
                }
            })

        return points

    def write(self, points):

        influx = self.influx_client()
        influx.write_points(points)

    def collect_metrics(self, day, dry_run):

        points = []
        today = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())

        click.echo("Collecting stats for day: %s" % day)

        if day == today:
            # No org creation date in db, can't get stats from the past
            orgs = self.get_organisms()
            click.echo("Found %s organisms: %s" % (len(orgs), orgs))

            points += self.prepare_influx_points("organisms", len(orgs), day)

        genes_by_orgs = self.get_genes_by_org(day)
        click.echo("Genes by orgs: %s" % genes_by_orgs)

        points += self.prepare_influx_points("genes", sum(genes_by_orgs.values()), day)

        points += self.prepare_influx_points_by_x("genes", genes_by_orgs, "organism", day)

        users_by_orgs = self.get_users_by_org(day)
        click.echo("Users by organisms: %s" % users_by_orgs)

        points += self.prepare_influx_points_by_x("users", users_by_orgs, "organism", day)

        genes_by_users = self.get_genes_by_users(day)
        click.echo("Genes by users: %s" % genes_by_users)

        if day == today:
            # No user creation date in db, can't get stats from the past
            users = self.get_users()
            points += self.prepare_influx_points("users", len(users), day)
            click.echo("Found %s users (%s active): %s" % (len(users), len(genes_by_users), users))

        points += self.prepare_influx_points("users_active", len(genes_by_users), day)

        points += self.prepare_influx_points_by_x("genes", genes_by_users, "user", day)

        click.echo("InfluxDB points: %s" % points)

        if not dry_run:
            click.echo("Writing to InfluxDB")
            self.write(points)
        else:
            click.echo("Not writing to InfluxDB (dry-run mode)")


@click.command()
@click.argument('db_string')
@click.argument('influx_host')
@click.argument('influx_port')
@click.argument('influx_db')
@click.argument('instance_name')
@click.option('--suffix', default="", help="Remove given suffix from user ids")
@click.option('--from-date', default="", help="Collect data from given date (format: YYYYMMDD, e.g. 20181025)")
@click.option('--to-date', default="", help="Collect data until given date (format: YYYYMMDD, e.g. 20181025)")
@click.option('-d', '--dry-run', help='Do not write any influxdb data, just fetch and print stats on stdout', is_flag=True)
def monitor(db_string, influx_host, influx_port, influx_db, instance_name, suffix, from_date, to_date, dry_run):
    mon = ApolloMonitor(db_string, influx_host, influx_port, influx_db, instance_name, suffix)

    days = []
    if from_date or to_date:

        if not from_date or not to_date:
            raise RuntimeError("Give a starting date %s AND an ending date %s" % (from_date, to_date))

        from_date = datetime.datetime.strptime(from_date, '%Y%m%d')
        to_date = datetime.datetime.strptime(to_date, '%Y%m%d')

        if from_date == to_date:
            raise RuntimeError("Give a starting date %s and an ending date %s that are different" % (from_date, to_date))

        if from_date > to_date:
            raise RuntimeError("Starting date %s should be before ending date %s" % (from_date, to_date))

        delta = to_date - from_date

        for i in range(delta.days + 1):
            day = from_date + datetime.timedelta(days=i)
            days.append(day)
    else:
        # Get today's date, at midnight
        days = [datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())]

    click.echo("Will run for the following day(s):")
    for day in days:
        print(day)

    for day in days:
        mon.collect_metrics(day, dry_run)


if __name__ == '__main__':
    monitor()
