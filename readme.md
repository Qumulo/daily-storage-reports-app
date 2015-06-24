## Requirements

* Qumulo cluster with API credentials
* Linux or Mac with continuous access to the Qumulo cluster
* cron
* sqlite3
* python
* python libraries: flask, argparse, sqlite
* Qumulo API python library
* Email smtp server or google apps credentials


## Installation

First, set up the required libraries on your Linux or Mac system.

### Linux, Ubuntu
```shell
sudo apt-get install python-pip sqlite3
pip install Flask
pip install argparse
```

### Mac OSX
```shell
sudo brew install python
sudo brew install sqlite3
pip install Flask
pip install argparse
```

### Set up the configuration file
Edit *config.json*
1. Add your Qumulo cluster information and credentials
2. Edit your email credentials/server

Setup crontab
Run *setup-crontab.sh* on the command line to install the scheduled data pulls in your crontab.

## Running the web app
```python app.py --op server```