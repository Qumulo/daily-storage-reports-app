(crontab -l ; echo "1 */6 * * * python $PWD/app.py --op api_pull --api_data dashstats,cluster_status,capacity_by_path")| crontab -
(crontab -l ; echo "* * * * * python app.py --op api_pull --api_data iops_by_path")| crontab -
(crontab -l ; echo "10 */6 * * * python app.py --op aggregate_data")| crontab -