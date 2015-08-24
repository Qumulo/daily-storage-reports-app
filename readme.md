# Daily Storage Reports Readme

## Requirements

* Qumulo cluster and API credentials for the cluster
* Linux or Mac with continuous access to the Qumulo cluster
* cron
* sqlite3
* python
* python libraries: flask, argparse, sqlite
* Qumulo API python library
* Email smtp server or google apps credentials


## Installation Steps

### 1. Install the daily_storage_reports
```shell
git clone git@github.com:Qumulo/daily_storage_reports.git
```
Or, download the zip file (https://github.com/Qumulo/daily_storage_reports/archive/master.zip) and unzip it to your machine where you will be running this tool.

### 2. Install Prequisites

We currently support Linux or MacOSX for running the Daily Storage Reports. In some cases, the following commands may show warnings when run, however, the required libraries should still be correctly installed.

#### On Linux (Ubuntu)
```shell
sudo apt-get install python-pip sqlite3 phantomjs
```

#### On Mac OSX
```shell
brew install python sqlite3 phantomjs
```

### 3. Install the prerequisite python libraries

Just run

```shell
pip install -r requirements.txt

```

to install the python prerequisites including the Qumulo REST API
wrapper.

### 4. Set up the configuration file
Edit *config.json*
1. Add your Qumulo cluster information and credentials as well as the email credentials/server. There are descriptions of all required properties. There is also an example of what a typical config file will look like inside of the *cnofig.json* file.

### 5. Setup crontab and the intitial data
Run *setup-crontab.sh* on the command line to install the scheduled data pulls in your crontab.
```shell
./setup-daily-reports.sh
```

### 6. Run the web app
```shell
python app.py --op server
```

## About the reports in the web app

Once you've launched the web app via step 6 above, you'll have access to the reports interface. If you're running from your local machine, the reports will be located at the URL: http://localhost:8080/ otherwise, replace localhost with the full hostname where you are running the app.

### Menu

#### Filters
Change the cluster if you have multiple Qumulo clusters. Change path to a path on the cluster to limit the report to that particular path and below. Filter to a particular date range with the calendar or type in a date in the yyyy-mm-dd format.

#### Email
Email a pdf of the current report being viewed. The report will come as an attached pdf and it will be filtered to the current filter settings.

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
