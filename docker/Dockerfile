FROM ubuntu:trusty

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -yq install \
    cron wget python-pip sqlite3 phantomjs unzip

RUN mkdir /app && \
    cd /tmp && \
    wget -O /tmp/master.zip https://github.com/Qumulo/daily_storage_reports/archive/master.zip && \
    cd /app && \
    unzip /tmp/master.zip -d /app && \
    rm -f /tmp/master.zip && \
    pip install -r /app/daily-storage-reports-app-master/requirements.txt

ADD config.json /app/daily-storage-reports-app-master/config.json
ADD run.sh /run.sh

RUN cd /app/daily-storage-reports-app-master && ./setup-daily-reports.sh

EXPOSE 8080
WORKDIR /app/daily-storage-reports-app-master
CMD ["/run.sh"]
