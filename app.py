import math
import time
import datetime
import flask
import json
import smtplib
import os
import subprocess
import argparse
import re

from apitocsv import ApiToCsv
from sqlitedb import SqliteDb
from dateutil.parser import parse
from flask import url_for

from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email import Encoders

app = flask.Flask(__name__)

app.config.update(dict(
    DEBUG=True,
))

app.config.from_envvar('FLASKR_SETTINGS', silent=True)

app.jinja_env.autoescape = False



def get_db(db_name):
    if not hasattr(flask.g, 'pg_db'):
        flask.g.db = SqliteDb(db_name)
    return flask.g.db


def get_config():
    with open('config.json', 'r') as config_file:    
        config = json.load(config_file)
        return config


def get_clusters():
    config = get_config()
    clusters = config["clusters"]
    return clusters


def get_cluster_db(cluster_num):
    clusters = get_clusters()
    return get_db( clusters[cluster_num]["sqlite_db_path"] )


def aggregate_day(db, the_day):
    print time.strftime('%H:%M:%S') + " - Aggregating day: " + the_day
    # get the most recent cluster status entries.

    db.import_table_for_date("dashstats", the_day)
    db.import_table_for_date("capacity_by_path", the_day)
    db.import_table_for_date("iops_by_path", the_day)
    db.import_table_for_date("iops_by_client_ip", the_day)
    db.import_table_for_date("cluster_status", the_day)

    db.fixup_paths()

    db.add_report_daily_metrics(the_day)
    db.add_report_hourly_metrics(the_day)
    db.add_report_daily_path_metrics(the_day)


def aggregate_data(cluster):
    db = SqliteDb(cluster["sqlite_db_path"], cluster["csv_data_path"])
    db.create_tables()
    schs = db.get_schemas()

    delta_day = datetime.timedelta(days=1)
    current_day = datetime.datetime.now() - datetime.timedelta(days=7)
    while current_day <= datetime.datetime.now():
        aggregate_day(db, current_day.strftime("%Y-%m-%d"))
        current_day += delta_day


def check_alerts():
    configs = get_config()

    alerts_sql = """
        SELECT *
        FROM alert_rule
        WHERE rule_status = 1
    """

    sqls = {}

    sqls["iops"] = """
        SELECT * 
        FROM (select path, level, round(sum(file_read+file_write+namespace_read+namespace_write)/60) iops 
        FROM iops_by_path 
        WHERE timestamp >= datetime('%(now)s', '-3 hour') 
        group by 1, 2) t 
        WHERE iops %(expr)s %(val)s
        AND path = '%(path)s'
        ORDER BY level
    """

    sqls["capacity"] = """
        SELECT *
        FROM
        (
        SELECT path
        , MAX(CASE WHEN timestamp = '2015-07-12' THEN total_used_capacity ELSE 0 END) used
        , MAX(CASE WHEN timestamp = '2015-07-12' THEN total_used_capacity ELSE 0 END)
        - MAX(CASE WHEN timestamp = '2015-07-11' THEN total_used_capacity ELSE 0 END) change
        FROM report_daily_path_metrics
        WHERE timestamp in ('2015-07-11', '2015-07-12')
        GROUP BY 1
        ) t
        WHERE change >= 1e11
    """

    for config in configs["clusters"]:
        db = SqliteDb(config["sqlite_db_path"], config["csv_data_path"])
        db.get_schemas()
        db.import_table_for_date("iops_by_path", datetime.datetime.now().strftime("%Y-%m-%d"))
        alerts = db.get_results(alerts_sql)
        for alert in alerts:
            alert["now"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql = sqls[alert["alert_type"]] % alert
            print sql
            filtered_rows = db.get_results(sql)
            print filtered_rows






@app.route('/get-data-json')
def get_data_json():
    cluster_num = int(flask.request.args.get('cluster_num', '0'))
    db = get_cluster_db(cluster_num)

    if flask.request.args.get('d', '') != '':
        args = {}
        query_type = flask.request.args.get('d', '')
        args["path"] = flask.request.args.get('path', '/')
        args["start_date"] = flask.request.args.get('start_date', '2015-06-01')
        args["end_date"] = flask.request.args.get('end_date', datetime.datetime.now().strftime("%Y-%m-%d"))
        the_data = db.get_data_for_chart(query_type, args)
        return flask.jsonify(the_data)
    else:
        return ""


@app.route('/email')
def send_email():
    config = get_config()

    cluster_num = int(flask.request.args.get('cluster_num', '0'))
    cluster_name = config["clusters"][cluster_num]["name"]
    path = flask.request.args.get('path', '/')
    start_date = flask.request.args.get('start_date', '2015-06-01')
    end_date = flask.request.args.get('end_date', datetime.datetime.now().strftime("%Y-%m-%d"))

    pdf_name = "qumulo-storage-report-%s-%s-%s-%s.pdf" % (re.sub("[^a-z0-9]+", "_", cluster_name.lower())
            , re.sub("[^a-z0-9]+", "_", path.lower())
            , re.sub("[^a-z0-9]+", "", start_date.lower())
            , re.sub("[^a-z0-9]+", "", end_date.lower())
            )

    cmd = ["phantomjs","phantom-screenshot.js"]
    qs = flask.request.query_string
    cmd.append( qs )
    cmd.append( pdf_name )
    p = subprocess.Popen(cmd, stdout = subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    out,err = p.communicate()

    username = config["email_account"]["account_username"]
    password = config["email_account"]["account_password"]
    fromaddr = config["email_account"]["from_email_address"]
    toaddrs  = flask.request.args.get('to', '').replace(" ", "").split(",")
    text = "The latest Qumulo Daily Storage report is attached.<br />\r\n"
    text += "Cluster Name: <b>" + cluster_name + "</b><br />\r\n"
    text += "Path: <b>" + path + "</b><br />\r\n"
    text += "Start Date: <b>" + start_date + "</b><br />\r\n"
    text += "End Date: <b>" + end_date + "</b><br />\r\n<br />\r\n"

    subject = "Qumulo %s Storage Report %s%s" % (cluster_name, start_date, end_date, " For Path: " + path if path != "/" else "")
    html_message = text
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = fromaddr

    html = """\
    <html>
      <head></head>
      <body>
        %s
      </body>
    </html>
    """ % (html_message)

    body = MIMEMultipart('alternative')
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    body.attach(part1)
    body.attach(part2)
    msg.attach(body)

    with open(pdf_name, "rb") as fil:
        attachFile = MIMEBase('application', 'pdf')
        attachFile.set_payload(fil.read())
        Encoders.encode_base64(attachFile)
        attachFile.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_name))
        msg.attach(attachFile)

    if ":465" in config["email_account"]["server"]:
        smtp = smtplib.SMTP_SSL(config["email_account"]["server"])
    else:
        smtp = smtplib.SMTP(config["email_account"]["server"])
    smtp.ehlo()
    smtp.login(username,password)
    smtp.sendmail(fromaddr, toaddrs, msg.as_string())
    smtp.quit()

    return out



@app.route('/')
def show_index():
    cluster_num = int(flask.request.args.get('cluster_num', '0'))
    db = get_cluster_db(cluster_num)
    date_data = db.get_data_for_chart("date_range")["data"][0]
    phantom = flask.request.args.get('phantom', 'no')
    base_path = flask.request.args.get('path', '/')
    def_end = date_data["end_date"]
    start_date = flask.request.args.get('start_date', date_data["start_date"])
    end_date = flask.request.args.get('end_date', def_end)
    cluster_name = get_clusters()[cluster_num]["name"]

    start_date_fmt = parse(start_date).strftime("%b %d, %Y")
    end_date_fmt = parse(end_date).strftime("%b %d, %Y")

    body_content = ""
    body_content += flask.render_template("line-chart.html"
                            , chart_name="Capacity Summary"
                            , chart_id="capacity")
    if base_path == "/":
        body_content += flask.render_template("line-chart.html"
                            , chart_name="Network Summary (Avg Throughput)"
                            , chart_id="throughput")

    body_content += flask.render_template("line-chart.html"
                            , chart_name="Activity Summary (Avg IOPS)"
                            , chart_id="iops")

    body_content += flask.render_template("line-chart.html"
                            , chart_name="File Activity (Avg IOPS)"
                            , chart_id="file_iops")

    return flask.render_template('report-template.html'
                            , base_path=base_path
                            , start_date=start_date
                            , end_date=end_date
                            , cluster_name=cluster_name
                            , clusters=get_clusters()
                            , cluster_num=cluster_num
                            , body=body_content
                            , phantom=phantom
                            , request_url=re.sub("(to|phantom)=[^&]+[&]*", "", flask.request.url)
                            , title="Qumulo Storage Status Report")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bring data from Qumulo Rest API to a CSV')
    parser.add_argument('--op', required=True, help='Operation for application. Valid values: server or api_pull or aggregate_data')
    parser.add_argument('--api_data', required=False, help='API data type(s) to pull (separate multiple by commas). Valid values:\ndashstats\ncluster_status\nsampled_files_by_capacity\nsampled_files_by_file\niops_by_path\ncapacity_by_path\napi_call_log')
    parser.add_argument('--timestamp', default=time.strftime('%Y-%m-%d %H:%M:%S'))
    args = parser.parse_args()
    config = get_config()

    if args.op == "api_pull":
        for cluster in config["clusters"]:
            # initialize Api to CSV.
            apicsv = ApiToCsv(cluster["hostname"], cluster["api_username"], cluster["api_password"], cluster["csv_data_path"])

            # set the timestamp for writign to CSVs where the API doesn't provide a timettamp
            apicsv.set_timestamp(args.timestamp)

            # loop through each API call operation
            for api_call in args.api_data.split(','):
                apicsv.get_data(api_call)

        # log the api call times to a csv upon completion of all work.
        apicsv.get_data("api_call_log")

    elif args.op == "aggregate_data":
        for cluster in config["clusters"]:
            aggregate_data(cluster)

    elif args.op == "server":
        app.run(host='0.0.0.0', port=8080, threaded=True)

    elif args.op == "alerts":
        check_alerts()



