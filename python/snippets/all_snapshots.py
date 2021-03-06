# Basic example for taking snapshots from all the online, unlocked cameras of an agent
# API endpoint and key are passed as first and second command line parameter
# Agent id is passed as third parameter
import sys
import requests

endpoint, api_key, agent_id = sys.argv[1:]

all_devices = requests.get(endpoint + f'agent/{agent_id}/device', headers={'X-Api-Key': api_key}).json()
types = requests.get(endpoint + 'type/device/detected', headers={'X-Api-Key': api_key}).json()
camera_types = [type_['id'] for type_ in types if 'snapshot' in type_['capabilities']]


def take_snapshot(device):
    response = requests.get(
        endpoint + f"agent/{agent_id}/device/{device['id']}/multimedia/camera/snapshot",
        headers={'X-Api-Key': api_key})

    extension = response.headers['content-type'].split('/')[-1]
    file_name = f"{device['display_name']}.{extension}"
    with open(file_name, 'wb') as image:
        image.write(response.content)
        print(f"Snapshot taken from {device['display_name']}")


for device in all_devices:
    try:
        if device['type']['detected_id'] in camera_types and 'ONLINE' == device['status']:
            if device['authentication_status'] in ('AUTHENTICATED', 'NO_AUTHENTICATION'):
                take_snapshot(device)
    except KeyError:
        pass  # just ignore ineligible devices

