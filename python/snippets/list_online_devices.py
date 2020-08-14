# Basic example for listing all the online devices of an agent
# API endpoint and key are passed as first and second command line parameter
# Agent id is passed as third parameter
import requests
import sys

endpoint = sys.argv[1]
api_key = sys.argv[2]
agent_id = sys.argv[3]

types = requests.get(endpoint + 'type/device/detected', headers={'X-Api-Key': api_key}).json()

types_dict = {}
for type_ in types:
    types_dict[type_['id']] = type_

all_devices = requests.get(endpoint + f'agent/{agent_id}/device', headers={'X-Api-Key': api_key}).json()

for device in all_devices:
    if 'ONLINE' == device.get('status', 'OFFLINE'):
        print(device['id'],
              device['display_name'],
              device['vendor'],
              types_dict[device.get('type', {}).get('detected_id', 0)]['identifier'],
              device['ip_addresses'][0])
