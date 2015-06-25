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

### 1. Install the daily\_storage\_reports
```shell
git clone git@github.com:Qumulo/daily\_storage\_reports.git
```
Or, download the zip file (https://github.com/Qumulo/daily\_storage\_reports/archive/initial_checkin.zip) and unzip it to your machine where you will be running this tool.

### 2. Install Prequisites

We currently support Linux or MacOSX for running the Daily Storage Reports.

#### On Linux (Ubuntu)
```shell
sudo apt-get install python-pip sqlite3
pip install Flask
pip install argparse
```

#### On Mac OSX
```shell
sudo brew install python
sudo brew install sqlite3
pip install Flask
pip install argparse
```

### 3. Install the Qumulo API python library
```shell
pip install qumulo_api
```

### 4. Set up the configuration file
Edit *config.json*
1. Add your Qumulo cluster information and credentials
2. Edit your email credentials/server

### 5. Setup crontab
Setup crontab
Run *setup-crontab.sh* on the command line to install the scheduled data pulls in your crontab.

### 6. Run the web app
```shell
python app.py --op server
```