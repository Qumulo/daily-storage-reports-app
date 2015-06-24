(crontab -l ; echo "* * * * * . $HOME/.bash_profile; cd $PWD; python app.py --op api_pull --api_data iops_by_path >> cron-api-data-1-minute.log 2>&1")| crontab -
(crontab -l ; echo "1 */6 * * * . $HOME/.bash_profile; cd $PWD; python app.py --op api_pull --api_data dashstats,cluster_status,capacity_by_path >> cron-api-data-6-hour.log 2>&1")| crontab -
(crontab -l ; echo "31 */6 * * * . $HOME/.bash_profile; cd $PWD; python app.py --op aggregate_data >> cron-api-aggregate-data.log 2>&1")| crontab -
