# Trivial example of listing all the enabled cameras in an agent
# API endpoint and key are passed as first and second command line parameter
# Agent id is passed as third parameter
import sys
import requests

endpoint, api_key, agent_id = sys.argv[1:]

all_devices = requests.get(endpoint + f'agent/{agent_id}/device', headers={'X-Api-Key': api_key}).json()
types = requests.get(endpoint + 'type/device/detected', headers={'X-Api-Key': api_key}).json()
camera_types = [type_['id'] for type_ in types if 'snapshot' in type_['capabilities']]


def print_camera(device):
    print(f"Device '{device['display_name']}' (id: {device['id']}) is a camera capable of taking snapshots")


for device in all_devices:
    try:
        if device['type']['detected_id'] in camera_types and 'ONLINE' == device['status']:
            if device['authentication_status'] in ('AUTHENTICATED', 'NO_AUTHENTICATION'):
                print_camera(device)
    except KeyError:
        pass  # just ignore ineligible devices
