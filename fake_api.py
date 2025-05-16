from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/')
def get_devices():
    client_code = request.args.get('client_code')
    if client_code == 'cliente01':
        return jsonify([
            {
                "nome_de_dispositivo": "EPSON2C64AA",
                "ip_address": "192.168.0.52",
                "parameter": [
                    {"parameter": "uptime", "mib": ".1.3.6.1.2.1.1.3.0"},
                    {"parameter": "mac_address", "mib": ".1.3.6.1.2.1.2.2.1.6.1"},
                    {"parameter": "in_octets", "mib": ".1.3.6.1.2.1.2.2.1.10.1"},
                    {"parameter": "out_octets", "mib": ".1.3.6.1.2.1.2.2.1.16.1"}
                ]
            }
        ])
    else:
        return jsonify([])


@app.route('/report', methods=['POST'])
def receive_report():
    data = request.json
    print("Recebido da aplicação:", data)
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(port=5000)
