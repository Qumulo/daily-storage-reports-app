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


def nice_bytes(n):
    sign = ""
    if n < 0:
        sign = "-"
        n = abs(n)

    pres = ["", "K", "M", "G", "T", "P"]
    if n < 1000:
        return sign + str(n) + " B"
    
    for i in range(0, len(pres)):
        if n >= math.pow(10, i*3) and n < math.pow(10, i*3+3):
            return sign + "{:.1f}".format(n / math.pow(10, i*3)) + " " + pres[i] + "B";


def bytes_to_num(s):
    pres = ["K", "M", "G", "T", "P"]
    for i, p in enumerate(pres):
        mm = re.search("([0-9.]+).*?" + p + "b", s, flags=re.IGNORECASE)
        if mm is not None:
            return float(mm.groups(1)[0]) * math.pow(10, 3*(i+1))
    return float(s)

def get_config():
    with open('config.json', 'r') as config_file:    
        config = json.load(config_file)
        return config


def get_clusters():
    config = get_config()
    clusters = config["clusters"]
    return clusters


def get_cluster_db(cluster_name):
    clusters = get_clusters()
    for cluster in clusters:
        if cluster["name"] == cluster_name:
            return get_db( cluster["sqlite_db_path"] )

def get_default_cluster():
    clusters = get_clusters()
    return clusters[0]["name"]

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
        AND send_count <= max_send_count
    """

    sqls = {}

    sqls["iops"] = """
        SELECT * 
        FROM (select path, level, round(sum(file_read+file_write+namespace_read+namespace_write)/60) val 
        FROM iops_by_path 
        WHERE timestamp >= datetime('%(now)s', '-3 hour') 
        group by 1, 2) t 
        WHERE val %(expr)s %(val)s
        AND path = '%(path)s'
        ORDER BY level
    """

    sqls["used capacity change"] = """
        SELECT *
        FROM
        (
        SELECT path
        , MAX(COALESCE(CASE WHEN timestamp = '%(today)s' THEN total_used_capacity ELSE 0 END, 0))
            - MAX(COALESCE(CASE WHEN timestamp = date('%(today)s', '-1 day') THEN total_used_capacity ELSE 0 END, 0)) val
        FROM report_daily_path_metrics
        WHERE timestamp in (date('%(today)s', '-1 day'), '%(today)s')
        GROUP BY 1
        ) t
    """

    sqls["total used capacity"] = """
        SELECT *
        FROM
        (
        SELECT path
        , MAX(COALESCE(CASE WHEN timestamp = '%(today)s' THEN total_used_capacity ELSE 0 END, 0)) val
        , MAX(COALESCE(CASE WHEN timestamp = date('%(today)s', '-1 day') THEN total_used_capacity ELSE 0 END, 0)) val_prior
        FROM report_daily_path_metrics
        WHERE timestamp in (date('%(today)s', '-1 day'), '%(today)s')
        GROUP BY 1
        ) t
        WHERE val %(expr)s %(val)s
        AND val_prior %(expr_inv)s %(val)s
        AND path = '%(path)s'
    """

    recipients = {}
    for config in configs["clusters"]:
        db = SqliteDb(config["sqlite_db_path"], config["csv_data_path"])
        db.get_schemas()
        db.import_table_for_date("iops_by_path", datetime.datetime.now().strftime("%Y-%m-%d"))
        alerts = db.get_results(alerts_sql)
        for alert in alerts:
            alert["now"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            alert["today"] = datetime.datetime.now().strftime("%Y-%m-%d")
            alert["expr_inv"] = "<" if alert["expr"] == ">=" else ">"
            sql = sqls[alert["alert_type"]] % alert
            filtered_rows = db.get_results(sql)
            if len(filtered_rows) > 0:
                for email in alert["recipients"].split(","):
                    if email not in recipients:
                        recipients[email] = [{"subject":alert["alert_type"], "body":build_alert_email(db, config, alert, filtered_rows)}]
                    else:
                        recipients[email].append({"subject":alert["alert_type"], "body":build_alert_email(db, config, alert, filtered_rows)})

    for email in recipients:
        mail_it(configs, email, '<br/>\r\n'.join(d["body"] for d in recipients[email]), "Qumulo " + config["name"] + " cluster alert: " + ', '.join(d["subject"] for d in recipients[email]))



def build_alert_email(db, config, alert, rows):
    msg = "The <b>%(alert_type)s</b> on the <b>%(cluster)s</b> cluster for the <b>%(path)s</b> path are <b>%(direction)s</b> %(threshold)s (currently: <b>%(val)s</b>)" % {
        "alert_type":alert["alert_type"], 
        "cluster":config["name"], 
        "path":alert["path"],
        "direction":"above" if alert["expr"] == ">=" else "below",
        "threshold":alert["val"] if alert["alert_type"] == "iops" else nice_bytes(alert["val"]),
        "val":rows[0]["val"] if alert["alert_type"] == "iops" else nice_bytes(rows[0]["val"])}
    return msg


def mail_it(config, toaddrs_str, text, subject):
    username = config["email_account"]["account_username"]
    password = config["email_account"]["account_password"]
    fromaddr = config["email_account"]["from_email_address"]
    toaddrs  = toaddrs_str.replace(" ", "").split(",")

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

    if ":465" in config["email_account"]["server"]:
        smtp = smtplib.SMTP_SSL(config["email_account"]["server"])
    else:
        smtp = smtplib.SMTP(config["email_account"]["server"])
    smtp.ehlo()
    smtp.login(username,password)
    smtp.sendmail(fromaddr, toaddrs, msg.as_string())
    smtp.quit()



@app.route('/get-data-json')
def get_data_json():
    cluster_name = flask.request.args.get('cluster_name', get_default_cluster())
    db = get_cluster_db(cluster_name)

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

@app.route('/alerts')
def manage_alerts():
    return flask.render_template('alerts.html', d={})

@app.route('/api-alerts', methods=['GET', 'POST'])
def api_alerts():
    configs = get_config()


    alerts_sql = """
        SELECT *
        FROM alert_rule
        WHERE rule_status = 1
    """

    all_alerts = []
    for config in configs["clusters"]:
        db = SqliteDb(config["sqlite_db_path"], config["csv_data_path"])
        db.get_schemas()

        if flask.request.method == "POST":
            if flask.request.form['action'] == "remove":
                id_parts = flask.request.form['id[]'].split("|")
                if id_parts[0] == config["name"]:
                    print "DELETE FROM alert_rule WHERE alert_id in (%s)" % (id_parts[1], )
            elif flask.request.form['action'] == "create":
                fd = flask.request.form
                ins_sql = """INSERT INTO alert_rule
                (created_timestamp, alert_type, path, expr, val, recipients, max_send_count, send_count)
                values
                ('%s', '%s',       '%s',     '%s',     %s, '%s',     %s,    %s)
                """
                sql = ins_sql % (
                    datetime.datetime.now().strftime("%Y-%m-%d")
                    , fd["data[alert_type]"]
                    , fd["data[path]"]
                    , fd["data[expr]"]
                    , bytes_to_num(fd["data[val]"])
                    , fd["data[recipients]"]
                    , fd["data[max_send_count]"]
                    , fd["data[send_count]"]
                )
                db.get_results(alerts_sql)


        alerts = db.get_results(alerts_sql)
        for alert in alerts:
            alert["cluster"] = config["name"]
            alert["val"] = alert["val"] if alert["alert_type"] == "iops" else nice_bytes(alert["val"])
            alert["alert_id"] = config["name"] + "|" + str(alert["alert_id"])
            all_alerts.append(alert)

    the_data = {"data":all_alerts}
    return flask.jsonify(the_data)



@app.route('/email')
def send_email():
    config = get_config()

    cluster_name = flask.request.args.get('cluster_name', get_default_cluster())
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
    cluster_name = flask.request.args.get('cluster_name', get_default_cluster())
    db = get_cluster_db(cluster_name)
    date_data = db.get_data_for_chart("date_range")["data"][0]
    phantom = flask.request.args.get('phantom', 'no')
    base_path = flask.request.args.get('path', '/')
    def_end = date_data["end_date"]
    start_date = flask.request.args.get('start_date', date_data["start_date"])
    end_date = flask.request.args.get('end_date', def_end)

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



