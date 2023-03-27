import argparse
import csv
import sys
import traceback
from typing import List, Dict

import requests

# Config section
datacenters = ['primal', 'aether', 'crystal', 'dynamis']
rate_limit = 10
priority_datacenter = 'primal'
fuzzy_rate = 90000

# Set up argument parser
parser = argparse.ArgumentParser(description='Parse a list.txt file.')
parser.add_argument('-o', '--options', action='store_true', help='Show options')
parser.add_argument('-f', '--file', type=str, help='Input file')
parser.add_argument('-p', '--pipe', action='store_true', help='Take input from pipe')
parser.add_argument('outputfile', type=str, help='Output file')
parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')
args = parser.parse_args()

if args.options:
    parser.print_help()
    sys.exit()

if args.file:
    with open(args.file, 'r') as f:
        input_data = f.read()
elif args.pipe:
    input_data = sys.stdin.read()
else:
    print('Error: No input specified')
    sys.exit()

# Parse input data
lines = input_data.split('\n')
items: List[Dict[str, str]] = []
for line in lines:
    if 'Dyes' in line:
        break
    if ':' in line:
        item_name, amount = line.split(':')
        item_name = item_name.strip()
        amount = int(amount.strip())
        items.append({'name': item_name, 'amount': amount})

# Get item IDs from xivapi
xivapi_url = 'https://xivapi.com/search'
for item in items:
    params = {'string': item['name'], 'indexes': 'item'}
    response = requests.get(xivapi_url, params=params)
    data = response.json()
    if data['Results']:
        item['item_id'] = data['Results'][0]['ID']
    else:
        print(f'Error: Could not find item ID for {item["name"]}')
        sys.exit()

# Get market data from universalis.app
universalis_url = 'https://universalis.app/api'
for item in items:
    lowest_price = None
    for datacenter in datacenters:
        url = f'{universalis_url}/{datacenter}/{item["item_id"]}'
        response = requests.get(url)
        data = response.json()
        if 'listings' in data and data['listings']:
            listings = sorted(data['listings'], key=lambda x: x['pricePerUnit'])
            if not lowest_price or listings[0]['pricePerUnit'] < lowest_price:
                lowest_price = listings[0]['pricePerUnit']
                item['market_price'] = lowest_price
                item['world_server'] = listings[0]['worldName']
                item['data_center'] = datacenter
    if not lowest_price:
        if args.verbose:
            print(f'\033[33mWarning: Could not find market data for {item["name"]}\033[0m')
        item['market_price'] = None
        item['world_server'] = None
        item['data_center'] = None
    else:
        item['total'] = item['market_price'] * item['amount']

# Write output to CSV file
with open(args.outputfile, 'w') as f:
    fieldnames = ['item_id', 'name', 'amount', 'market_price', 'world_server', 'data_center', 'total']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for item in items:
        writer.writerow(item)

if args.verbose:
    print(f'\033[32mSuccessfully wrote output to {args.outputfile}\033[0m')