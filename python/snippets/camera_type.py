# Trivial example for listing all the device types that can take snapshots (e.g. ONVIF cameras)
# API endpoint and key are passed as first and second command line parameter
import sys
import requests

endpoint = sys.argv[1]
api_key = sys.argv[2]
types = requests.get(endpoint + 'type/device/detected', headers={'X-Api-Key': api_key}).json()
for type_ in types:
    if 'snapshot' in type_['capabilities']:
        print(type_['id'], type_['identifier'])
