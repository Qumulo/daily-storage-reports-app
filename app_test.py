import unittest
from unittest.mock import call, patch, MagicMock

from app import *

class AppTest(unittest.TestCase):
    def test_nice_bytes(self):
        self.assertEqual(nice_bytes(0), '0 B')
        self.assertEqual(nice_bytes(1000), '1.00 KB')
        self.assertEqual(nice_bytes(2000 * 1000), '2.00 MB')
        self.assertEqual(nice_bytes(3000 * 1000 * 1000), '3.00 GB')
        self.assertEqual(nice_bytes(4000 * 1000 * 1000 * 1000), '4.00 TB')
        self.assertEqual(nice_bytes(5000 * 1000 * 1000 * 1000 * 1000), '5.00 PB')

    def test_bytes_to_num(self):
        self.assertEqual(bytes_to_num('0'), 0)
        self.assertEqual(bytes_to_num('1KB'), 1000)
        self.assertEqual(bytes_to_num('2MB'), 2000000)
        self.assertEqual(bytes_to_num('3GB'), 3000000000)
        self.assertEqual(bytes_to_num('4TB'), 4000000000000)
        self.assertEqual(bytes_to_num('5PB'), 5000000000000000)

    @patch('qumulo.rest_client.RestClient')
    def test_check_config_success(self, rest_client_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        with patch('apitocsv.ApiToCsv.get_cluster_status'):
            self.assertEqual(check_config(), 0)

    def test_check_config_bad_connection(self):
        self.assertEqual(check_config(), 102)

    def test_get_config(self):
        self.assertEqual(
            get_config()['clusters'][0]['name'], '<Friendly name of the Qumulo Cluster>'
        )

    def test_get_clusters(self):
        self.assertEqual(
            get_clusters()[0]['name'], '<Friendly name of the Qumulo Cluster>'
        )

    def test_get_default_cluster(self):
        self.assertEqual(get_default_cluster(), '<Friendly name of the Qumulo Cluster>')

    @patch('app.aggregate_day')
    def test_aggregate_data(self, aggregate_day_mock):
        db_path = os.path.join(os.getcwd(), 'test.db')
        cluster = { 'sqlite_db_path': db_path, 'csv_data_path': '2020-02-20-test.csv' }

        aggregate_data(cluster)

        self.assertEqual(aggregate_day_mock.call_count, 8)

        os.remove(db_path)

    @patch('app.mail_it')
    @patch('sqlitedb.SqliteDb.get_results')
    @patch('qumulo.rest_client.RestClient')
    def test_check_alerts(self, rest_client_mock, result_mock, mail_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        result_mock.return_value = [
            { 'recipients': 'r1', 'expr': '>', 'alert_type': 'iops', 'val': 1000, 'path': '/path/1', 'alert_id': 1 },
        ]

        check_alerts()

        self.assertEqual(mail_mock.call_args[0][1],  'r1')
        self.assertIn('/path/1</b> path are <b>below 1000',  mail_mock.call_args[0][2])
        self.assertIn('Qumulo Quota Alert: iops',  mail_mock.call_args[0][3])

        db_path = get_clusters()[0]['sqlite_db_path']
        os.remove(db_path)

    @patch('qumulo.rest_client.RestClient')
    def test_main_verify_config(self, rest_client_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        with patch('apitocsv.ApiToCsv.get_cluster_status'):
            main(['--op', 'verify_config'])

    @patch('apitocsv.ApiToCsv.get_data')
    @patch('qumulo.rest_client.RestClient')
    def test_main_api_pull(self, rest_client_mock, data_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        main(['--op', 'api_pull', '--api-data', 'cluster_status', 'iops_by_path'])

        self.assertEqual(
            data_mock.call_args_list,
            [ call('cluster_status'), call('iops_by_path'), call('api_call_log') ]
        )

    @patch('apitocsv.ApiToCsv.set_timestamp')
    @patch('apitocsv.ApiToCsv.get_data')
    @patch('qumulo.rest_client.RestClient')
    def test_main_api_pull_with_timestamp(self, rest_client_mock, data_mock, timestamp_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        main(['--op', 'api_pull', '--api-data', 'dashstats', '--timestamp', '2020-02-20 10:10:10'])

        self.assertEqual(
            data_mock.call_args_list, [ call('dashstats'), call('api_call_log') ]
        )
        self.assertEqual(timestamp_mock.call_args[0][0], '2020-02-20 10:10:10')

    @patch('app.aggregate_data')
    def test_main_aggregate_data(self, aggregate_data_mock):
        main(['--op', 'aggregate_data'])

        self.assertEqual(aggregate_data_mock.call_count, 1)

    @patch('app.app.run')
    def test_main_server(self, app_run_mock):
        main(['--op', 'server'])

        self.assertEqual(app_run_mock.call_args, call(host='0.0.0.0', port=8080, threaded=True))

    @patch('app.check_alerts')
    def test_main_alerts(self, check_alerts_mock):
        main(['--op', 'alerts'])

        self.assertEqual(check_alerts_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
