import sqlite3
import csv
import sys
import glob
import datetime
from collections import OrderedDict

class SqliteDb(object):

    db_path = None
    cn = None
    cn_c = None
    data_dir = None

    tables = [
    {
    "name":"capacity_by_path",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            , levels INT
            , inode_path VARCHAR(2048)
            , total_capacity BIGINT
            , total_directories INT
            , total_files INT
        )
        """},
    {
    "name":"dashstats",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            ,  iops_read FLOAT
            ,  iops_write FLOAT
            ,  throughput_read FLOAT
            ,  throughput_write FLOAT
        )
        """},
    {
    "name":"cluster_status",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            , total_raw_capacity BIGINT 
            , total_usable_capacity BIGINT
            , total_used_capacity BIGINT
            , nodes_status VARCHAR(512)
            )
        """},
    {
    "name":"iops_by_path",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            ,  level INT
            ,  path VARCHAR(2048)
            ,  total FLOAT
            ,  file_read FLOAT
            ,  file_write FLOAT
            ,  namespace_read FLOAT
            ,  namespace_write FLOAT
        )
        """},
    {
    "name":"iops_by_client_ip",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            , ip VARCHAR(28)
            , total FLOAT
            , file_read FLOAT
            , file_write FLOAT
            , namespace_read FLOAT
            , namespace_write FLOAT
        )
        """},
    {
    "name":"sampled_files_by_capacity",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            , inode_id INT
            , name VARCHAR(2048)
            , extension VARCHAR(10)
            , size BIGINT
            , mode INT
            , last_modified VARCHAR(54)
            , group_id BIGINT
            , owner_id BIGINT )
        """},
    {
    "name":"sampled_files_by_file",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATETIME
            , inode_id INT
            , name VARCHAR(2048)
            , extension VARCHAR(10)
            , size BIGINT
            , mode INT
            , last_modified VARCHAR(54)
            , group_id BIGINT
            , owner_id BIGINT 
        )
        """},
    {
    "name":"report_daily_metrics",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATE
            , total_used_capacity BIGINT
            , total_usable_capacity BIGINT 
            , avg_read_iops FLOAT
            , avg_write_iops FLOAT
            , avg_read_throughput FLOAT
            , avg_write_throughput FLOAT
        )
        """},
    {
    "name":"report_hourly_metrics",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATE
            , avg_read_iops FLOAT
            , avg_write_iops FLOAT
            , avg_read_throughput FLOAT
            , avg_write_throughput FLOAT
        )
        """},
    {
    "name":"report_daily_path_metrics",
    "create_sql":"""
        CREATE TABLE %(table_name)s ( 
            timestamp DATE
            , path_level
            , path VARCHAR(2048)
            , total_used_capacity BIGINT
            , avg_iops FLOAT
            , avg_file_read_iops FLOAT
            , avg_file_write_iops FLOAT
        )
        """},
    {
    "name":"alert_rule",
    "create_sql":"""
        CREATE TABLE %(table_name)s (
            alert_id INTEGER PRIMARY KEY 
            , created_timestamp DATETIME
            , alert_type VARCHAR(16)
            , path VARCHAR(2048)
            , expr VARCHAR(6) 
            , val BIGINT
            , recipients VARCHAR(2048)
            , send_count INT
            , max_send_count INT
            , rule_status INT
            , last_send_timestamp DATETIME
        )
        """}
    ]

    schemas = {}


    def __init__(self, db_path, data_dir="/tmp/"):

        self.db_path = db_path
        self.cn = sqlite3.connect(self.db_path)
        self.cn.row_factory = self.dict_factory
        self.cn_c = self.cn.cursor()
        self.data_dir = data_dir

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def create_tables(self):
        for table in self.tables:
            try:
                self.cn_c.execute(table["create_sql"] % {"table_name":table["name"]})
                self.cn.commit()
            except sqlite3.OperationalError:
                # Table already exists
                pass
 

    def get_schemas(self):
        for table in self.tables:
            cols = OrderedDict()
            for row in self.cn_c.execute("PRAGMA table_info(%(table_name)s)" % {"table_name":table["name"]}):
                cols[row["name"]] = {"name":row["name"], "pos":row["cid"], "type":row["type"]}
            self.schemas[table["name"]] = cols
        return self.schemas


    def get_insert_sql(self, table_name):
        sql = "INSERT INTO %(table_name)s VALUES (%(ins_cols)s)" % {"table_name":table_name, "ins_cols":','.join(["?"] * len(self.schemas[table_name]))}
        return sql


    def add_report_daily_metrics(self, the_date):
        sql = """
            INSERT INTO report_daily_metrics
            SELECT '%(d)s', used_capacity, usable_capacity, iops_read, iops_write, throughput_read, throughput_write
            FROM 
            (
            select avg(total_capacity) used_capacity 
            FROM capacity_by_path 
            WHERE levels=1 AND inode_path='/'
            ) c
            LEFT JOIN 
            (
            select total_usable_capacity usable_capacity 
            from cluster_status 
            WHERE timestamp = (select max(timestamp) from cluster_status)
            ) d ON 1 = 1
            LEFT JOIN 
            (
            SELECT 
            avg(iops_read) iops_read
            , avg(iops_write) iops_write
            , avg(throughput_read) throughput_read
            , avg(throughput_write) throughput_write
            FROM dashstats
            ) e ON 1 = 1
        """
        self.cn_c.execute("DELETE FROM report_daily_metrics WHERE timestamp='%(d)s'" % {"d":the_date})
        self.cn_c.execute(sql % {"d":the_date})
        self.cn.commit()


    def add_report_hourly_metrics(self, the_date):
        sql = """
            INSERT INTO report_hourly_metrics
            SELECT strftime('%%Y-%%m-%%d %%H:00:00', timestamp)
                    , avg(iops_read) iops_read
                    , avg(iops_write) iops_write
                    , avg(throughput_read) throughput_read
                    , avg(throughput_write) throughput_write
                    FROM dashstats
            GROUP BY strftime('%%Y-%%m-%%d %%H:00:00', timestamp)
            """
        self.cn_c.execute("DELETE FROM report_hourly_metrics WHERE strftime('%%Y-%%m-%%d', timestamp)='%(d)s'" % {"d":the_date})
        self.cn_c.execute(sql % {"d":the_date})
        self.cn.commit()


    def add_report_daily_path_metrics(self, the_date):
        sql = """
            INSERT INTO report_daily_path_metrics
            SELECT '%(d)s', *
            FROM
            (

            SELECT COALESCE(level, levels) level, COALESCE(path, inode_path) path, used_capacity, avg_iops, avg_file_read_iops, avg_file_write_iops
            FROM
            (
            SELECT levels, inode_path, avg(total_capacity) used_capacity FROM capacity_by_path GROUP BY levels, inode_path
            ) a
            LEFT JOIN
            (
            SELECT level, path
            , sum(COALESCE(file_read + file_write + namespace_read + namespace_write, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_iops 
            , sum(COALESCE(file_read, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_file_read_iops 
            , sum(COALESCE(file_write, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_file_write_iops 
            FROM iops_by_path GROUP BY level, path
            ) b ON inode_path = path

            UNION ALL

            SELECT COALESCE(level, levels) level, COALESCE(path, inode_path) path, used_capacity, avg_iops, avg_file_read_iops, avg_file_write_iops
            FROM
            (
            SELECT level, path
            , sum(COALESCE(file_read + file_write + namespace_read + namespace_write, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_iops 
            , sum(COALESCE(file_read, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_file_read_iops 
            , sum(COALESCE(file_write, 0)) / (SELECT count(distinct timestamp) cnt FROM iops_by_path) avg_file_write_iops 
            FROM iops_by_path GROUP BY level, path
            ) a
            LEFT JOIN
            (
            SELECT levels, inode_path, avg(total_capacity) used_capacity FROM capacity_by_path GROUP BY levels, inode_path
            ) b ON inode_path = path
            WHERE b.inode_path IS NULL
            ) t

            """
        self.cn_c.execute("DELETE FROM report_daily_path_metrics WHERE timestamp='%(d)s'" % {"d":the_date})
        self.cn_c.execute(sql % {"d":the_date})
        self.cn.commit()


    def import_table_for_date(self, table_name, the_date):
        sql = "DELETE FROM %(table_name)s WHERE timestamp >= '%(the_date)s' AND timestamp < datetime('%(the_date)s', '24 HOUR') " % {"table_name":table_name, "the_date":the_date}
        self.cn_c.execute(sql)
        self.cn.commit()

        insert_sql = self.get_insert_sql(table_name)
        rows_to_insert = []

        files = glob.glob(self.data_dir + "/" + the_date + "-" + table_name + "*.csv")
        for f_name in files:
            with open(f_name) as csv_file:
                csv_reader = csv.reader(csv_file)
                csv_reader.next()
                row_count = 0
                for row in csv_reader:
                    if len(row) == 0 or len(row) != len(self.schemas[table_name]):
                        continue
                    rows_to_insert.append([unicode(cell if cell is not None else '', 'utf-8') for cell in row])
                    row_count += 1
                    # batches of 1000 records
                    if row_count % 1000 == 0:
                        self.cn_c.executemany(self.get_insert_sql(table_name), rows_to_insert)
                        self.cn.commit()
                        rows_to_insert = []
                # Get the leftovers
                self.cn_c.executemany(self.get_insert_sql(table_name), rows_to_insert)
                self.cn.commit()


    def fixup_paths(self):
        sql = "DELETE FROM capacity_by_path WHERE inode_path LIKE '%/' AND inode_path <> '/'"
        self.cn_c.execute(sql)
        self.cn.commit()
        sql = "UPDATE capacity_by_path SET levels = 0 WHERE inode_path = '/'"
        self.cn_c.execute(sql)
        self.cn.commit()


    def get_data_for_chart(self, data_query, args={}):
        sqls = {}

        sqls["capacity"] = """
                select timestamp, MAX(CASE WHEN path = '%(path)s' THEN total_used_capacity ELSE 0 END) total_used_capacity
                from report_daily_path_metrics 
                WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s'
                GROUP BY 1
                ORDER BY 1
        """

        sqls["iops"] = """
                select timestamp
                , MAX(CASE WHEN path = '%(path)s' THEN round(avg_iops) ELSE 0 END) avg_iops
                from report_daily_path_metrics 
                WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s'
                GROUP BY 1
                ORDER BY 1
        """

        sqls["file_iops"] = """
                select timestamp
                , MAX(CASE WHEN path = '%(path)s' THEN round(avg_file_read_iops) ELSE 0 END) avg_file_read_iops
                , MAX(CASE WHEN path = '%(path)s' THEN round(avg_file_write_iops) ELSE 0 END) avg_file_write_iops
                from report_daily_path_metrics 
                WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s'
                GROUP BY 1
                ORDER BY 1
        """

        sqls["throughput"] = """
                select strftime('%%Y-%%m-%%d', timestamp) timestamp
                , avg(avg_read_throughput) avg_read_throughput
                , avg(avg_write_throughput) avg_write_throughput
                , max(avg_read_throughput) max_read_throughput
                , max(avg_write_throughput) max_write_throughput
                from report_hourly_metrics 
                WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s 23:59:59'
                GROUP BY 1
                ORDER BY 1
        """

        sqls["path_stats"] = """
            SELECT path_level, t.path, t1.total_used_capacity cap
            , COALESCE(t1.total_used_capacity, 0) - COALESCE(t0.total_used_capacity, 0) cap_chg
            , round(t.sum_iops / timestamp_count) avg_iops
            FROM
            (
            SELECT path_level, path, sum(avg_iops) sum_iops
            FROM report_daily_path_metrics 
            WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s'
            GROUP BY 1, 2
            ) t
            JOIN (
            select count(distinct timestamp) timestamp_count
            FROM report_daily_path_metrics 
            WHERE timestamp BETWEEN '%(start_date)s' AND '%(end_date)s'
            ) ts ON timestamp_count > 0
            LEFT JOIN (
            SELECT path, total_used_capacity
            FROM report_daily_path_metrics 
            WHERE timestamp = '%(start_date)s'
            ) t0 ON t0.path = t.path
            LEFT JOIN (
            SELECT path, total_used_capacity
            FROM report_daily_path_metrics 
            WHERE timestamp = '%(end_date)s'
            ) t1 ON t1.path = t.path
            WHERE t.path LIKE '%(path)s%%'
            ORDER BY path_level, t0.total_used_capacity DESC
            LIMIT 1000
        """

        sqls["date_range"] = """
            select min(timestamp) start_date, max(timestamp) end_date 
            from report_daily_path_metrics
        """

        # end date can't be in the future
        if "end_date" in args and args["end_date"] > datetime.datetime.now().strftime("%Y-%m-%d"):
            args["end_date"] = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = sqls[data_query] % args
        self.cn_c.execute(sql)
        rows = self.cn_c.fetchall()
        return {"sql": sql, "data": rows, "cluster":self.get_cluster_metrics()}


    def get_results(self, sql):
        self.cn_c.execute(sql)
        rows = self.cn_c.fetchall()
        return rows

    def query(self, sql):
        self.cn_c.execute(sql)
        self.cn.commit()


    def get_cluster_metrics(self):
        sql = """
                select total_usable_capacity 
                FROM cluster_status 
                WHERE timestamp = (select max(timestamp) FROM cluster_status);
        """
        self.cn_c.execute(sql)
        row = self.cn_c.fetchall()[0]
        return row

