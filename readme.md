# Deprecation Notice

**This software will shortly be deprecated and archived. If you have any issues, please reach out to [Michael Kade](mailto:mkade@qumulo.com) directly.**

# Daily Storage Reports

The Daily Storage Report is a standalone python flask app that uses the Qumulo API, CSVs, and SQLite to report on your Qumulo cluster(s) capacity and activity.

**NOTE** Daily Storage Reports requires **Python Version 3.4.11**

**Daily Storage Report features**:

* View and filter historical capacity and IOPS data.
* Email PDF reports to people who don't use the web-based interface.
* Set email alerts (soft quotas) on capacity usage, capacity change, and IOPS.
* View breakdowns in capacity usage and activity by path across the cluster.
* Report on multiple Qumulo clusters from one interface.
* Powered by the Qumulo API.

## Screenshots

![Capacity trend graph](/images/capacity-trend.png)

![Directory breakdown graph](/images/directory-breakdown.png)

![Network throughput graph](/images/network-throughput.png)


## Requirements

* Qumulo cluster and API credentials for the cluster
* Linux or Mac with continuous access to the Qumulo cluster
* cron
* sqlite3
* python3
* phantomjs
* python libraries: flask, argparse, sqlite
* Qumulo API python library
* Email smtp server or google apps credentials


## Installation Steps

### 1. Install the daily_storage_reports
```shell
git clone https://github.com/Qumulo/daily_storage_reports.git
```
Or, download the zip file (https://github.com/Qumulo/daily_storage_reports/archive/master.zip) and unzip it to your machine where you will be running this tool.

### 2. Install Prequisites

We currently support Linux or MacOSX for running the Daily Storage Reports. In some cases, the following commands may show warnings when run, however, the required libraries should still be correctly installed.

#### On Linux (Ubuntu)
```shell
sudo apt-get install python3-pip sqlite3 phantomjs
```

#### On Mac OSX
```shell
sudo brew install python3 sqlite3 phantomjs
```

### 3. Install the prerequisite python libraries

Just run

```shell
sudo pip3 install -r requirements.txt
```

to install the python prerequisites including the Qumulo REST API
wrapper.  *NOTE* that the daily_storage_reports sample requires Qumulo REST API version 4.0.0 or later.

### 4. Set up the configuration file
Edit *config.json*
1. Add your Qumulo cluster information and credentials as well as the email credentials/server. There are descriptions of all required properties. All settings are required, so make sure to replace all the values in the <> brackets. There is also an example of what a typical config file will look like inside of the *config.json.sample* file.

### 5. Setup crontab and the intitial data
Run *setup-crontab.sh* on the command line to install the scheduled data pulls in your crontab.
```shell
./setup-daily-reports.sh
```

### 6. Run the web app
```shell
python3 app.py --op server
```

To run in a background thread:

```shell
nohup python3 app.py --op server &
```
### 7. Supporting multiple users

The [guidance](http://flask.pocoo.org/docs/0.10/deploying/#deployment) from the developers of Flask is that
you should not deploy your app into production using Flask's built-in webserver; Specifically: 
they say:

    "You can use the builtin server during development, but you should use a full deployment option for production applications. (Do not use the builtin development server in production.)"
    
So for production scenarios you should consider using [uWSGI](http://flask.pocoo.org/docs/0.10/deploying/uwsgi/)
with ngnx or perhaps [mod_wsgi](http://flask.pocoo.org/docs/0.10/deploying/mod_wsgi/) for Apache environments, or
another option. For simplicity's sake (easy to get up and running) I'm using [Gunicorn](http://docs.gunicorn.org/en/19.3/),
 which is another WSGI server.  Starting and running using `gunicorn` is simple:
 
     gunicorn -b 0.0.0.0:8000 -w 4 --threads 4 -t 360 --access-logfile ~/ftt_log.txt manage:app
     
will start the server with four workers with four threads per worker at port 8000.

If you want to go uWSGI/nginx route, a good 'how to' document for ubuntu can be found [here](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-14-04).

Short of creating a WSGI-based deployment, you can run FTT in non-developer/debug mode and support simultaneous users, you 
should start the server using the following form/command (from http://goo.gl/A3YfNt):

```./manage.py runserver --host 0.0.0.0 --threaded```

or

```./manage.py runserver --host 0.0.0.0 --processes=[n]```

where

```[n]```  is some integer value such as 3,10 etc.  

using ```--host 0.0.0.0``` makes the host visible to other machines.


## About the reports in the web app

Once you've launched the web app via step 6 above, you'll have access to the reports interface. If you're running from your local machine, the reports will be located at the URL: http://localhost:8080/ otherwise, replace localhost with the full hostname where you are running the app.


#### Filters
Change the cluster if you have multiple Qumulo clusters. Change path to a path on the cluster to limit the report to that particular path and below. Filter to a particular date range with the calendar or type in a date in the yyyy-mm-dd format.

#### Email Report
Email a pdf of the current report being viewed. The report will come as an attached pdf and it will be filtered to the current filter settings.

#### Manage Alerts
Soft quota, email-based alerts can be managed here. Set up alerts based on total used capacity, capacity change, and iops. See "Alerts" section below for more.

### Capacity Summary
View the usage of the cluster's storage capacity over time, or for the particular path you are filtered to. The "Last 4 Weeks" metric in the "Growth Per Week" is a weekly average for the last four weeks. If "Last Week" is greater than "Last 4 Weeks", then it means you're capacity usage is accelerating.

### Network Summary (Avg Throughput)
View the average daily network usage over time. This graph will only show up if you are viewing the full cluster's stats with the "/" path.

### Activity Summary (Avg IOPS)
View the cluster (or filtered path) average daily IOPS over time.

### File Activity (Avg IOPS)
View the cluster (or filtered path) average daily file read and write IOPS over time. File read and write IOPS can be used to approximate throughput assuming an average block size of 500kb. 1000 IOPS * 500kb would be 500MB/s throughput.

### Capacity and IOPS Details by Directory
This table shows a detiled breakdown of path metrics for the cluster or filtered path.
* Level - The level of the directory with zero being the root (/) directory
* Path - The directory path on the cluster
* Capacity - The capacity used by the directory and its children for the last date of the report. If the capacity column shows "[Deleted]", there is a chance the directory exists, but that it is now smaller than the minimum capacity (0.05% of total used capacity) for tracking over time.
* Capacity Change - The change in used capacity for the directory and its children between the first and last date of the report.
* IOPS - The average IOPS for the directory and its children during the date range of the report.
* **Click on the Capacity, Capacity Change, or IOPS value to set up a new email alert.**

## Alerts
Alerts are email-based "soft quota" alerts which will notify the email recipient when certain metrics break a threshold. Alerts can be configured on "total used capacity", "used capacity change", and "iops".

Cluster - the cluster name as defined in the config file
Alert Type - "total used capacity", "used capacity change", and "iops"
Path - The file path to set the alert on. Cluster-wide alerts would be "/
Expression - Check whether a value is greater than or less than
Value - A numeric value. For capacity, units are bytes.
Recipients - Comma-separated list of email addresses.
Max Send Count - To limit the number of sends on an alert. If it's 1, only one email alert will get sent. Set it to something larger to get more emails for the same alert.
Send Count - The number of times an email has been sent for the alert.
