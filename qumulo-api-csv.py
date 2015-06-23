import argparse
import time
from apitocsv import ApiToCsv


def main(): 

    ## command line arguments
    parser = argparse.ArgumentParser(description='Bring data from Qumulo Rest API to a CSV')
    parser.add_argument('--cluster', required=True, help='The hostname of the Qumulo cluster')
    parser.add_argument('--username', required=True, help='Qumulo API username')
    parser.add_argument('--password', required=True, help='Qumulo API password')
    parser.add_argument('--op', required=True, help='API operation (separate multiple by commas). Valid values:\ndashstats\ncluster_status\nsampled_files_by_capacity\nsampled_files_by_file\niops_by_path\ncapacity_by_path\napi_call_log')
    parser.add_argument('--csvdir', required=True, help='Save files to this directory')
    parser.add_argument('--timestamp', default=time.strftime('%Y-%m-%d %H:%M:%S'))
    args = parser.parse_args()

    # initialize Api to CSV.
    apicsv = ApiToCsv(args.cluster, args.username, args.password, args.csvdir)

    # set the timestamp for writign to CSVs where the API doesn't provide a timettamp
    apicsv.set_timestamp(args.timestamp)

    # loop through each API call operation
    for op in args.op.split(','):
        apicsv.get_data(op)

    # log the api call times to a csv upon completion of all work.
    apicsv.get_data("api_call_log")


if __name__ == "__main__":
    main()

