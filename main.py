import configparser
import requests
from pysnmp.hlapi import *


def load_config(path='config.ini'):
    config = configparser.ConfigParser()
    config.read(path)
    return config['DEFAULT']


def get_devices_from_api(config):
    headers = {
        'X-API-KEY': config['api_key'],
        'X-API-SECRET': config['api_secret']
    }
    url = f"{config['service_url']}?client_code={config['client_code']}"
    response = requests.get(url, headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response text: {response.text}")
    response.raise_for_status()
    return response.json()


def snmp_get(ip, oid, community='public'):
    try:
        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((ip, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

        if errorIndication:
            return f"SNMP error: {errorIndication}"
        elif errorStatus:
            return f"SNMP error: {errorStatus.prettyPrint()}"
        else:
            for varBind in varBinds:
                return str(varBind[1])
    except Exception as e:
        return f"Exception: {e}"


def send_data_to_api(config, data):
    url = config['service_url'] + "/report"
    headers = {
        'X-API-KEY': config['api_key'],
        'X-API-SECRET': config['api_secret'],
        'Content-Type': 'application/json'
    }
    payload = {
        'client_code': config['client_code'],
        'data': data
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def main():
    config = load_config()
    devices = get_devices_from_api(config)

    collected_data = []

    for device in devices:
        device_name = device['nome_de_dispositivo']
        ip = device['ip_address']
        parameters = device['parameter']

        param_data = []
        for param in parameters:
            oid = param['mib']
            label = param['parameter']
            value = snmp_get(ip, oid)
            param_data.append({
                'parameter': label,
                'value': value
            })

        collected_data.append({
            'device': device_name,
            'ip': ip,
            'parameters': param_data
        })

    send_data_to_api(config, collected_data)
    print("Dados enviados com sucesso.")


if __name__ == '__main__':
    main()
