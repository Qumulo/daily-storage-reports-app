import time
import os
import csv
import sys
import re
import string
import dateutil.parser

from collections import OrderedDict
from qumulo.rest_client import RestClient

class ApiToCsv:

    api_cli = None
    data_dir = None
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    datestamp = None
    username = None
    password = None

    ## specific to capcity crawl
    searched_paths = {}
    files_added = {}

    api_call_times = {}

    def __init__(self, cluster, username, password, data_dir):
        self.username = username
        self.password = password
        self.api_cli = RestClient(cluster, 8000)
        self.qumulo_api_call(self.api_cli.login, username=username, password=password)
        self.data_dir = data_dir
        self.datestamp = self.timestamp[:10]


    def set_timestamp(self, new_timestamp):
        self.timestamp = dateutil.parser.parse(new_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        self.datestamp = self.timestamp[:10]


    def add_data(self, csv_file, d):
        file_exists = False
        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)
        csv_full_path = self.data_dir + "/" + csv_file
        if os.path.isfile(csv_full_path):
            file_exists = True
        f = open(csv_full_path, "ab")
        csv_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            csv_writer.writerow(d.keys())
        csv_writer.writerow([unicode(s).encode("utf-8") for s in d.values()])    
        f.close()


    def qumulo_api_call(self, f, **kwargs):
        start = time.clock()
        res = f(**kwargs)
        f_name = str(f.__name__)
        if f_name not in self.api_call_times:
            self.api_call_times[f_name] = []
        self.api_call_times[f_name].append((time.clock() - start)*1000)
        return res

    def get_api_call_log(self, table_name):
        for call_name in self.api_call_times:
            d = OrderedDict()
            d["timestamp"] = self.timestamp
            d["call_name"] = call_name
            d["call_count"] = len(self.api_call_times[call_name])
            d["avg_call_time"] = sum(self.api_call_times[call_name]) / float(len(self.api_call_times[call_name]))
            self.add_data(self.datestamp + "-" + table_name + ".csv", d)


    def get_data(self, api_call_name):
        print time.strftime('%Y-%m-%d %H:%M:%S') + " - Pulling csv data for: " + api_call_name
        f = getattr(self, 'get_' + api_call_name)
        f(api_call_name)


    def get_latest_date_dashstats_file(self, csv_file):
        file_path = self.data_dir + "/" + csv_file
        if os.path.isfile(file_path):
            f_stats = os.stat(file_path)
            seek_back = 5000
            if f_stats.st_size < seek_back:
                seek_back = f_stats.st_size
            f = open(self.data_dir + "/" + csv_file, "r")
            f.seek(-seek_back, os.SEEK_END)
            line = f.readlines()[-1]
            return re.search("([^,]*),", line).group(1)

        return "2000-01-01 00:00:00"


    def get_dashstats(self, table_name, time_inteval_seconds=5):
        api_begin_time = int(time.time()-60*60*25) # 24 hours of data, the max Qumulo stores

        # handle multiple api versions
        try:
            time_series_get_func = self.api_cli.stats.time_series_get
        except AttributeError:
            time_series_get_func = self.api_cli.analytics.time_series_get
        res = self.qumulo_api_call(time_series_get_func, begin_time=api_begin_time)
        metrics = {"iops.read.rate":"iops_read", "iops.write.rate":"iops_write", "throughput.read.rate":"throughput_read", "throughput.write.rate":"throughput_write"}
        files = {}
        for d in res:
            if d['id'] in metrics:
                for i in range(0,len(d['values'])):
                    t = time.localtime(d['times'][i+1])
                    if int(time.strftime('%M%S', t)) % time_inteval_seconds == 0:
                        t_key = time.strftime('%Y-%m-%d %H:%M:%S', t)
                        file_date = t_key[:10]
                        if file_date not in files:
                            files[file_date] = OrderedDict()
                        if t_key not in files[file_date]:
                            files[file_date][t_key] = OrderedDict()
                            files[file_date][t_key]['timestamp'] =  t_key
                        files[file_date][t_key][metrics[d['id']]] = d['values'][i]

        for file_date in files:
            csv_file = file_date + "-" + table_name + ".csv"
            latest_date = self.get_latest_date_dashstats_file(csv_file)
            for d in files[file_date].values():
                if d['timestamp'] > latest_date:
                    self.add_data(csv_file, d)


    def get_cluster_status(self, table_name):
        cluster_stats = self.qumulo_api_call(self.api_cli.fs.read_fs_stats)
        node_stats = self.qumulo_api_call(self.api_cli.cluster.list_nodes)
        d = OrderedDict()
        d["timestamp"] = self.timestamp
        d["total_raw_capacity"] = cluster_stats["raw_size_bytes"]
        d["total_usable_capacity"] = cluster_stats["total_size_bytes"]
        d["total_used_capacity"] = int(cluster_stats["total_size_bytes"]) - int(cluster_stats["free_size_bytes"])
        d["nodes_status"] = '{' + ','.join(["1" if st["node_status"] == "online" else "0" for st in node_stats]) + '}'
        self.add_data(self.datestamp + "-" + table_name + ".csv", d)


    def get_sampled_files(self, table_name, by_type, start_dir, sample_count):
        arr = self.qumulo_api_call(self.api_cli.fs.get_file_samples, path=start_dir, by_value=by_type, count=sample_count)
        for f in arr:
            d = OrderedDict()
            # file might no longer exist.
            try:
                attrs = self.qumulo_api_call(self.api_cli.fs.get_attr, id_ = f['id'])
            except:
                continue
            d['timestamp'] = self.timestamp
            d["inode_id"] = f['id']
            d["inode_name"] = f["name"]
            ext = os.path.splitext(f['name'])[1]
            if len(ext) > 5:
                ext = ""
            d["extension"] = ext
            d["group_id"] = int(attrs["group"]) - (4 << 32)
            d["owner_id"] = int(attrs["owner"]) - (3 << 32)
            mod_time = dateutil.parser.parse(attrs["modification_time"])
            d["last_modified"] = mod_time.strftime("%Y-%m-%d %H:%M:%S")
            d["mode"] = attrs["mode"]
            d["size"] = f["capacity_usage"]
            self.add_data(self.datestamp + "-" + table_name+ ".csv", d)


    def get_sampled_files_by_file(self, table_name, start_dir="/", sample_count=1000):
        self.get_sampled_files(table_name, "file", start_dir, sample_count)


    def get_sampled_files_by_capacity(self, table_name, start_dir="/", sample_count=1000):
        self.get_sampled_files(table_name, "capacity", start_dir, sample_count)


    #  Get sampled IOPS data 
    def get_iops_by_path(self, table_name):
        # Pull IOPS data for all types (namespace read/write and file read/write)
        # Handle multiple API versions
        try:
            iops_get_func = self.api_cli.stats.iops_get
        except AttributeError:
            iops_get_func = self.api_cli.analytics.iops_get
        res = self.qumulo_api_call(iops_get_func)

        ip_iops = {}
        # Resolve inode ids to file paths
        ids = []
        iops_types = OrderedDict([("read","file_read"), ("write","file_write"), ("namespace-read","namespace_read"), ("namespace-write","namespace_write")])
        for iop in res['entries']:
            ids.append(iop["id"])
        ids = list(set(ids))
        self.qumulo_api_call(self.api_cli.login, username = self.username, password = self.password)
        id_path_arr = self.qumulo_api_call(self.api_cli.fs.resolve_paths, ids = ids)
        id_paths = {}
        for id_path in id_path_arr:
            id_paths[id_path['id']] = id_path['path']

        # Now we can loop through the IOPS data
        all_iops = {}
        total_iops = 0
        for iop in res['entries']:
            if iop["type"] not in iops_types:
                continue

            if iop['ip'] not in ip_iops:
                data = OrderedDict()
                data['timestamp'] = self.timestamp
                data['ip'] = iop['ip']
                data['total'] = 0
                for iops_type in iops_types.values():
                    data[iops_type] = 0
                ip_iops[iop['ip']] = data
            ip_iops[iop['ip']]['total'] += iop['rate']
            ip_iops[iop['ip']][iops_types[iop["type"]]] += iop['rate']
                

            path_parts = string.split(id_paths[iop['id']], '/')

            for ppi in range(1,len(path_parts)):
                if ppi == 1:
                    the_path = '/'
                else:
                    the_path = '/'.join(path_parts[0:ppi])

                if the_path not in all_iops:
                    data = OrderedDict()
                    data['timestamp'] = self.timestamp
                    data['level'] = ppi - 1
                    data['path'] = the_path
                    data['total'] = 0
                    for iops_type in iops_types.values():
                        data[iops_type] = 0
                    all_iops[the_path] = data

                all_iops[the_path]['total'] += iop['rate']
                all_iops[the_path][iops_types[iop["type"]]] += iop['rate']

            total_iops += iop['rate']

        for k, v in all_iops.iteritems():
            if v['total'] > total_iops * 0.01:
                self.add_data(self.datestamp + "-" + table_name + ".csv", v)

        # a little bonus!
        for k, v in ip_iops.iteritems():
            if v['total'] > total_iops * 0.005:
                self.add_data(self.datestamp + "-iops_by_client_ip.csv", v)


    def get_capacity_by_path(self, table_name, start_path = "/", grand_total_capcity=-1):
        if start_path in self.searched_paths:
            return
        # Stop at 12 levels deep.
        if start_path.count ('/') > 12:
            return
        self.searched_paths[start_path] = 1
        # Waiting on the api unicode fix
        try:
            res = self.qumulo_api_call(self.api_cli.fs.read_dir_aggregates, path=unicode(start_path), recursive=False, max_entries=1000, max_depth=8, order_by="total_blocks")
        except:
            return

        ent = res
        if ent['path'] == '/' and grand_total_capcity == -1:
            grand_total_capcity = float(ent['total_capacity'])

        if float(ent['total_capacity']) / grand_total_capcity >= 0.001:
            data = OrderedDict()
            data["timestamp"]=self.timestamp
            data["levels"]=ent['path'].count ('/')
            data["inode_path"]=ent['path']
            data["total_capacity"]=int(ent['total_capacity'])
            data["total_directories"]=int(ent['total_directories'])
            data["total_files"]=int(ent['total_files'])

            if ent['path'] not in self.files_added:
                self.add_data(self.datestamp + "-" + table_name+ ".csv", data)
                self.files_added[ent['path']] = 1

        for f in ent['files']:
            full_path = re.sub("[/]+", "/", ent['path'] + f['name'])
            if float(f['capacity_usage']) / grand_total_capcity >= 0.001:
                data = OrderedDict()
                data["timestamp"]=self.timestamp
                data["levels"]=full_path.count ('/')
                data["inode_path"]=full_path
                data["total_capacity"]=int(f['capacity_usage'])
                data["total_directories"]=int(f['num_directories'])
                data["total_files"]=int(f['num_files'])

                if full_path not in self.files_added:
                    self.add_data(self.datestamp + "-" + table_name+ ".csv" , data)
                    self.files_added[full_path] = 1

            if float(f['capacity_usage']) / grand_total_capcity > 0.001:
                self.get_capacity_by_path(table_name, ent['path'] + f['name'], grand_total_capcity)

