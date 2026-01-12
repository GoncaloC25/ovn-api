from flask import Flask, jsonify, request
from flask_cors import CORS
from ovsdbapp.backend.ovs_idl import connection
from ovsdbapp.schema.ovn_northbound import impl_idl

conn = "tcp:127.0.0.1:6641"

i = connection.OvsdbIdl.from_server(conn, 'OVN_Northbound')
c = connection.Connection(idl=i, timeout=3)
api = impl_idl.OvnNbApiIdlImpl(c)

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "conected", "db": "ovn-nb"})

@app.route("/switch", methods=["GET"])
def list_switch():
    return jsonify([ls.name for ls in api.ls_list().execute()])

@app.route("/switch/<switch_name>/ports", methods=["GET"])
def list_ports(switch_name):
    ports = api.lsp_list(switch_name).execute()
    result = []
    for port in ports:
        result.append({
            "name": port.name,
            "addresses": port.addresses
        })
    return jsonify(result)

@app.route("/switch/<switch_name>/vlans", methods=["GET"])
def list_switch_vlans(switch_name):
    ports = api.lsp_list(switch_name).execute()
    result = []
    for port in ports:
        vlan_tag = getattr(port, 'tag', None)
        trunks = getattr(port, 'trunks', None)
        if trunks is not None:
            trunks = list(trunks)
        result.append({
            "name": port.name,
            "vlan_tag": vlan_tag,
            "trunks": trunks,
        })
    return jsonify(result)

@app.route("/switch/<switch_name>/acl", methods=["GET"])
def list_acl(switch_name):
    acls = api.acl_list(switch_name).execute()
    result = []
    for acl in acls:
        result.append({
            "direction": acl.direction,
            "match": acl.match,
            "action": acl.action,
	    "priority": acl.priority
        })
    return jsonify(result)



@app.route("/switch", methods=["POST"])
def add_switch():
    data = request.json
    api.ls_add(data["name"]).execute()
    return jsonify({"status": "created", "switch": data["name"]})

@app.route("/switch/<switch_name>/ports", methods=["POST"])
def add_ports(switch_name):
    data = request.json
    api.lsp_add(switch_name, data["port-name"]).execute()
    mac=data["mac-address"]
    ip=data["ip"]
    api.lsp_set_addresses(
	data["port-name"],
	[f"{mac} {ip}"]
    ).execute()
    return jsonify({"status": "created", "port": data["port-name"]})

@app.route("/switch/<switch_name>/acl", methods=["POST"])
def add_acl(switch_name):
    data = request.json
    api.acl_add(
        switch=switch_name,
        direction=data["direction"]+"-lport",
        priority=data["priority"],
        match=data["match"],
        action=data["action"]
    ).execute()
    return jsonify({"status": "created", "switch": switch_name, "direction": data["direction"], "match": data["match"], "action": data["action"]})

@app.route("/switch/<switch_name>/<port_num>/vlan", methods=["POST"])
def add_vlan(switch_name, port_num):
    data = request.json
    api.db_set(
        "Logical_Switch_Port",
        switch_name + "-port" + port_num,
        ("tag", data["vlan"])
    ).execute()
    return jsonify({"status": "created", "switch": switch_name, "port": "port "+port_num, "vlan-tag": data["vlan"]})



@app.route("/switch/<switch_name>", methods=["DELETE"])
def del_switch(switch_name):
    api.ls_del(switch_name).execute()
    return jsonify({"status": "deleted", "switch": switch_name})

@app.route("/switch/<switch_name>/<port_num>", methods=["DELETE"])
def del_port(switch_name, port_num):
    api.lsp_del(switch_name + "-port" + port_num).execute()
    return jsonify({"status": "deleted", "port": switch_name + "-port" + port_num})

@app.route("/switch/<switch_name>/<port_num>/vlan", methods=["DELETE"])
def del_port_vlan(switch_name, port_num):
    return jsonify({"status": "not yet integrated"})

@app.route("/switch/<switch_name>/acl", methods=["DELETE"])
def del_acl(switch_name):
    data = request.json
    api.acl_del(
        switch_name,
	data["direction"] + "-lport",
	data["priority"],
	data["match"]
    ).execute()
    return jsonify({"status": "deleted", "from-switch": switch_name})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
