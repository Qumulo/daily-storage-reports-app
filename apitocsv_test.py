import os
import unittest
from unittest.mock import patch

from apitocsv import *

@patch('qumulo.rest_client.RestClient')
class ApiToCsvTest(unittest.TestCase):
    def tearDown(self):
        for path in os.listdir(os.getcwd()):
            if path.endswith('.csv'):
                os.remove(path)

    def setup_test(self, rest_client_mock):
        rest_client_mock.return_value = rest_client_mock
        rest_client_mock.login.__name__ = 'login'

        atc = ApiToCsv('cluster', 'admin', 'a', os.getcwd())
        return atc

    def test_timestamp(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)
        atc.set_timestamp('2020-02-20 10:10:10')

        self.assertEqual(atc.timestamp, '2020-02-20 10:10:10')
        self.assertEqual(atc.datestamp, '2020-02-20')

    def test_add_data(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        csv_file_path = 'test.csv'
        atc.add_data(csv_file_path, {'k1': 'v1', 'k2': 'v2'})
        with open(csv_file_path, 'r') as csv_file:
            self.assertEqual(csv_file.read(), 'k1,k2\nv1,v2\n')

    def test_qumulo_api_call(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        # We've logged in once from initializing the ApiToCsv object
        self.assertEqual(len(atc.api_call_times['login']), 1)

        atc.qumulo_api_call(rest_client_mock.login)
        self.assertEqual(len(atc.api_call_times['login']), 2)

        rest_client_mock.some_other_api.__name__ = 'some_other_api'
        atc.qumulo_api_call(rest_client_mock.some_other_api)
        self.assertEqual(len(atc.api_call_times['some_other_api']), 1)

    def test_get_api_call_log(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)
        
        rest_client_mock.some_other_api.__name__ = 'some_other_api'
        atc.qumulo_api_call(rest_client_mock.some_other_api)

        atc.set_timestamp('2020-02-20 10:10:10')
        atc.get_api_call_log('test')

        with open('2020-02-20-test.csv', 'r') as csv_file:
            data = csv_file.read()
            self.assertIn(
                'timestamp,call_name,call_count,avg_call_time\n'
                '2020-02-20 10:10:10,login,1,',
                data
            )
            self.assertIn('2020-02-20 10:10:10,some_other_api,1,', data)

    def test_get_latest_date_dashstats_file(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        atc.set_timestamp('2020-02-20 10:10:10')
        atc.get_api_call_log('test')

        date = atc.get_latest_date_dashstats_file('2020-02-20-test.csv')
        self.assertEqual(date, '2020-02-20 10:10:10')

    def test_get_latest_date_dashstats_file_no_get_api_call_log(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        csv_file_path = 'test.csv'
        atc.add_data(csv_file_path, {'k1': 'v1', 'k2': 'v2'})
        with open(csv_file_path, 'r') as csv_file:
            self.assertEqual(csv_file.read(), 'k1,k2\nv1,v2\n')

        date = atc.get_latest_date_dashstats_file('csv_file_path')
        self.assertEqual(date, '2000-01-01 00:00:00')


    def test_set_dashstats_with_analytics_time_series(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        def get_time_series_data(**kwargs):
            return [
                {
                    'id': 'iops.read.rate',
                    'times': [ 0, 1500000000],
                    'values': [ .5, ]
                },
                {
                    'id': 'iops.write.rate',
                    'times': [ 0, 1500000000 ],
                    'values': [ 8 ]
                },
                {
                    'id': 'not_real_metric',
                    'times': [ 9, 9, 9 ],
                    'values': [ .1, .1, .1 ]
                },
            ]
        rest_client_mock.stats.time_series_get.side_effect = get_time_series_data
        rest_client_mock.stats.time_series_get.__name__ = 'time_series_get'

        atc.get_dashstats('test') 

        [csv_path] = [path for path in os.listdir(os.getcwd()) if path.endswith('.csv')]
        with open(csv_path, 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,iops_read,iops_write\n2017-07-13 19:40:00,0.5,8\n'
            )

    def test_get_cluster_status(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        def get_read_fs_stats(**kwargs):
            return {
                'block_size_bytes': 4096,
                'free_size_bytes': '100',
                'snapshot_size_bytes': '200',
                'total_size_bytes': '300'
            }
        rest_client_mock.fs.read_fs_stats.side_effect = get_read_fs_stats
        rest_client_mock.fs.read_fs_stats.__name__ = 'read_fs_stats'

        def get_list_nodes(**kwargs):
            return [
                {
                    'node_status': 'online'
                },
                {
                    'node_status': 'offline'
                }
            ]
        rest_client_mock.cluster.list_nodes.side_effect = get_list_nodes
        rest_client_mock.cluster.list_nodes.__name__ = 'list_nodes'

        atc.set_timestamp('2020-02-20 10:10:10')
        cluster_status = atc.get_cluster_status('test')

        with open('2020-02-20-test.csv', 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,total_raw_capacity,total_usable_capacity,total_used_capacity,nodes_status\n'
                '2020-02-20 10:10:10,300,300,200,"{1,0}"\n'
            )

    def test_get_sampled_files(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        def get_sampled_files(**kwargs):
            return [
                {
                    'capacity_usage': 1234,
                    'id': 1,
                    'name': 'file1'
                },
            ]
        rest_client_mock.fs.get_file_samples.side_effect = get_sampled_files
        rest_client_mock.fs.get_file_samples.__name__ = 'file_samples'

        def get_attr(**kwargs):
            return {
                'group': 513,
                'owner': 500,
                'modification_time': '2021-05-14T21:38:46.59687791Z',
                'mode': '0777'
            }

        rest_client_mock.fs.get_attr.side_effect = get_attr
        rest_client_mock.fs.get_attr.__name__ = 'get_attr'


        atc.set_timestamp('2020-02-20 10:10:10')
        atc.get_sampled_files('test', 'capacity', '/', 2)

        with open('2020-02-20-test.csv', 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,inode_id,inode_name,extension,group_id,owner_id,last_modified,mode,size\n'
                '2020-02-20 10:10:10,1,file1,,-17179868671,-12884901388,2021-05-14 21:38:46,0777,1234\n'
            )

    def test_get_iops_by_path(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        def get_iops(**kwargs):
            return {
                'entries': [
                    {
                        'id': 1,
                        'ip': '1.1.1.1',
                        'rate': .05,
                        'type': 'read'
                    },
                    {
                        'id': 2,
                        'ip': '2.2.2.2',
                        'rate': .05,
                        'type': 'write'
                    }
                ]
            }
        rest_client_mock.stats.iops_get.side_effect = get_iops
        rest_client_mock.stats.iops_get.__name__ = 'iops_get'

        def resolve_path(ids):
            paths = []
            for file_id in ids:
                paths.append({ 'id': file_id, 'path': f'/path/{file_id}/' })
            return paths
        rest_client_mock.fs.resolve_paths.side_effect = resolve_path
        rest_client_mock.fs.resolve_paths.__name__ = 'resolve_paths'

        atc.set_timestamp('2020-02-20 10:10:10')
        atc.get_iops_by_path('test')

        with open('2020-02-20-test.csv', 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,level,path,total,file_read,file_write,namespace_read,namespace_write\n'
                '2020-02-20 10:10:10,0,/,0.1,0.05,0.05,0,0\n'
                '2020-02-20 10:10:10,1,/path,0.1,0.05,0.05,0,0\n'
                '2020-02-20 10:10:10,2,/path/1,0.05,0.05,0,0,0\n'
                '2020-02-20 10:10:10,2,/path/2,0.05,0,0.05,0,0\n'
            )

        with open('2020-02-20-iops_by_client_ip.csv', 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,ip,total,file_read,file_write,namespace_read,namespace_write\n'
                '2020-02-20 10:10:10,1.1.1.1,0.05,0.05,0,0,0\n'
                '2020-02-20 10:10:10,2.2.2.2,0.05,0,0.05,0,0\n'
            )

    def test_get_capacity_by_path(self, rest_client_mock):
        atc = self.setup_test(rest_client_mock)

        def get_read_dir_aggregates(**kwargs):
            return {
                'files': [
		    {
			'capacity_usage': '4096',
			'data_usage': '0',
			'id': '1',
			'name': 'one',
			'num_directories': '0',
			'num_files': '1',
		    },
		    {
			'capacity_usage': '4096',
			'data_usage': '0',
			'id': '2',
			'name': 'two',
			'num_directories': '3',
			'num_files': '1',
		    }
                ],
		'id': '3',
		'path': '/',
		'total_capacity': '100',
		'total_data': '50',
		'total_directories': '6',
		'total_files': '80',
            }

        rest_client_mock.fs.read_dir_aggregates.side_effect = get_read_dir_aggregates
        rest_client_mock.fs.read_dir_aggregates.__name__ = 'read_dir_aggregates'

        atc.set_timestamp('2020-02-20 10:10:10')
        atc.get_capacity_by_path('test')

        with open('2020-02-20-test.csv', 'r') as csv_file:
            self.assertEqual(
                csv_file.read(),
                'timestamp,levels,inode_path,total_capacity,total_directories,total_files\n'
                '2020-02-20 10:10:10,1,/,100,6,80\n'
		'2020-02-20 10:10:10,1,/one,4096,0,1\n'
		'2020-02-20 10:10:10,1,/two,4096,3,1\n'
            )

if __name__ == '__main__':
    unittest.main()
