import json

from flask import Flask, send_file, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def get_remote_address():
    return request.remote_addr

limiter = Limiter(get_remote_address)
limiter.init_app(app)

def reload_updates():
    with open('files/Updates.json', 'r') as f:
        data = json.load(f)

    return dict(
        sorted(
            data.items(),
            key=lambda item: tuple(map(int, item[0].split("."))),
            reverse=True
        )
    )

def parse_version(version: str):
    return tuple(map(int, version.split(".")))


def get_updates_range(from_version: str, to_version: str):
    # fallback if target version is invalid
    if to_version not in versions:
        to_version = versions[0]

    # If client version is older than oldest known version,
    # send ALL updates
    if (
        from_version not in versions and
        parse_version(from_version) < parse_version(versions[-1])
    ):
        from_index = len(versions)

    # unknown newer version
    elif from_version not in versions:
        from_index = 1

    else:
        from_index = versions.index(from_version)

    to_index = versions.index(to_version)

    selected_versions = versions[to_index:from_index]

    return {
        version: updates[version]["content"]
        for version in selected_versions
    }

def update_range_required(from_version):
    if not from_version in versions:
        from_version = versions[-1]

    from_index = versions.index(from_version)

    for version in versions[0:from_index]:
        required = updates[version]["required"]
        if required:
            return True
    return False

@app.route("/download/launcher", methods=["GET"])
@limiter.limit("1 per second")
def download_launcher():
    return send_file("files/Gamenest.zip", as_attachment=True)

@app.route("/download/updater", methods=["GET"])
@limiter.limit("1 per second")
def download_updater():
    return send_file("files/updater.zip", as_attachment=True)

@app.route("/update_content", methods=["GET"])
@limiter.limit("3 per second")
def update_content():
    from_version = request.args.get("from_version", default=versions[1])
    to_version = request.args.get("to_version", default=versions[0])
    content = get_updates_range(from_version, to_version)
    reversed_content = dict(reversed(list(content.items())))
    return jsonify(reversed_content), 200

def get_last_required_version():
    for version in versions:
        if updates[version].get("required", False):
            return version
    return versions[-1]

@app.route("/launcher_version", methods=["GET"])
@limiter.limit("2 per second")
def launcher_version():
    current_version = request.args.get("current_version", default=versions[1])
    required = False
    if update_range_required(current_version):
        required = True
    return jsonify({"version": versions[0], "last_required": required}), 200

if __name__ == "__main__":
    updates = reload_updates()
    versions = list(updates.keys())
    app.run(host='0.0.0.0', port=11283, debug=False)
