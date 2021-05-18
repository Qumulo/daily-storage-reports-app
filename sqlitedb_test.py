import os
import unittest
from unittest.mock import call, patch, MagicMock

from sqlitedb import SqliteDb

class SqliteDbTest(unittest.TestCase):
    def tearDown(self):
        for path in os.listdir(os.getcwd()):
            if path.endswith('.db'):
                os.remove(path)

    def test_create_tables(self):
        db = SqliteDb('test.db')
        db.tables = [{'create_sql': 'CREATE','name': 'test_table'}]
        db.create_tables()
        self.assertIn('test_table', db.get_schemas())

    def test_get_schemas(self):
        db = SqliteDb('test.db')
        self.assertTrue(
            set(db.get_schemas().keys()).issubset([
                'test_table',
                'capacity_by_path',
                'dashstats',
                'cluster_status',
                'iops_by_path',
                'iops_by_client_ip',
                'sampled_files_by_capacity',
                'sampled_files_by_file',
                'report_daily_metrics',
                'report_hourly_metrics',
                'report_daily_path_metrics',
                'alert_rule'
            ])
        )

    def test_get_insert_sql(self):
        db = SqliteDb('test.db')
        self.assertEqual(
            db.get_insert_sql('test_table'), 'INSERT INTO test_table VALUES ()'
        )

    @patch('sqlite3.connect')
    def test_fixup_paths(self, sql_mock):
        connection_mock = MagicMock()
        sql_mock.return_value = connection_mock

        cursor_mock = MagicMock()
        connection_mock.cursor.return_value = cursor_mock

        db = SqliteDb('test.db')
        db.fixup_paths()
        self.assertIn('UPDATE capacity_by_path', cursor_mock.execute.call_args[0][0])

    @patch('sqlite3.connect')
    def test_get_data_for_chart(self, sql_mock):
        db = SqliteDb('test.db')
        args = {
            'path': '/path/1',
            'start_date': '2020-02-20',
            'end_date': '2021-02-20'
        }

        data = db.get_data_for_chart('iops', args)
        self.assertIn("WHERE timestamp BETWEEN '2020-02-20' AND '2021", data['sql'])

    def test_get_results(self):
        db = SqliteDb('test.db')
        rows = db.get_results('SELECT 1+1')
        self.assertEqual(rows, [{ '1+1': 2 }])

    @patch('sqlite3.connect')
    def test_get_cluster_metrics(self, sql_mock):
        db = SqliteDb('test.db')
        rows = db.get_cluster_metrics()
        self.assertEqual(rows, -1)


if __name__ == '__main__':
    unittest.main()
