import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import requests
import sys
from pysnmp.hlapi import (
    CommunityData, UdpTransportTarget,
    ContextData, ObjectType, ObjectIdentity, getCmd
)


if getattr(sys, 'frozen', False):
    log_path = os.path.join(os.path.dirname(sys.executable), "snmp_log.txt")
else:
    log_path = os.path.join(os.getcwd(), "snmp_log.txt")

print("Log path:", log_path)

logger = logging.getLogger("snmp_logger")
logger.setLevel(logging.INFO)

try:
    handler = logging.FileHandler(log_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    print("FileHandler attached to logger.")
except Exception as e:
    print(f"Erro ao inicializar FileHandler: {e}")
    logger.addHandler(logging.StreamHandler())
    print("StreamHandler (stdout) attached to logger.")

print("Logger handlers:", logger.handlers)


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
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info("Dispositivos obtidos da API: %s", url)
        return response.json()
    except Exception as e:
        logger.error("Erro ao obter dispositivos da API:%s", e)
        print(f"Erro ao obter dispositivos da API: {e}")
        return []


def snmp_get(ip, oid, community='public'):
    try:
        iterator = getCmd(
            CommunityData(community, mpModel=1),
            UdpTransportTarget((ip, 161), timeout=2, retries=2),
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )

        errorIndication, errorStatus, _, varBinds = next(iterator)

        if errorIndication:
            logger.error("SNMP error [%s - %s]: %s", ip, oid, errorIndication)
            print("SNMP error [%s - %s]: %s", ip, oid, errorIndication)
            return None
        elif errorStatus:
            logger.error(
                "SNMP error [%s - %s]: %s", ip, oid, errorStatus.prettyPrint())
            print(f"SNMP error [{ip} - {oid}]: {errorStatus.prettyPrint()}")
            return None
        else:
            for varBind in varBinds:
                return str(varBind[1])
    except Exception as e:
        logger.error("Exceção SNMP [%s - %s]: %s", ip, oid, e)
        print(f"Exceção SNMP [{ip} - {oid}]: {e}")
    return None


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
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info("Dados enviados com sucesso para %s", url)
        return response.json()
    except Exception as e:
        logger.error("Erro ao enviar dados para a API: %s", e)
        print(f"Erro ao enviar dados para a API: {e}")
        return None


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

    result = send_data_to_api(config, collected_data)

    if result is not None:
        print("Status code: 200")
        print(f"Response text: {collected_data}")
        print("Dados enviados com sucesso.")
        logger.info("Execução concluída com sucesso.")
    else:
        print("Falha ao enviar dados.")
        logger.warning("Execução concluída com falha no envio.")

    # Garante que o log é gravado antes de sair
    for handler in logger.handlers:
        handler.flush()
    logging.shutdown()
    input("Pressione Enter para sair...")


if __name__ == '__main__':
    main()
