QPROFILEPATH=$(ls -1ra ~/.*profile* | tail -1)

python app.py --op verify_config
RESULT=$?
if [ $RESULT -ne 0 ] ; then
    echo "********** config.json verification failed! **********"
    echo "Check your installation, settings and/or fix the config.json file and run this script again."
    exit 1
fi

python app.py --op api_pull --api-data iops_by_path
python app.py --op api_pull --api-data {dashstats,cluster_status,capacity_by_path}
python app.py --op aggregate_data

# Pull IOPS data from the qumulo cluster once per minute
(crontab -l ; echo "* * * * * . $QPROFILEPATH; cd $PWD; python app.py --op api_pull --api-data iops_by_path >> cron-api-data-1-minute.log 2>&1")| crontab -
# Pull capacity and activity data from the qumulo every six hours
(crontab -l ; echo "1 */6 * * * . $QPROFILEPATH; cd $PWD; python app.py --op api_pull --api-data {dashstats,cluster_status,capacity_by_path} >> cron-api-data-6-hour.log 2>&1")| crontab -
# Aggregate Qumulo csv data every six hours
(crontab -l ; echo "31 */6 * * * . $QPROFILEPATH; cd $PWD; python app.py --op aggregate_data >> cron-api-aggregate-data.log 2>&1")| crontab -
