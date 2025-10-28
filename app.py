from flask import Flask, render_template, send_from_directory, jsonify, abort
import jinja2
import refreshgcov
import os
import logging
import ssh

ssh_client = None

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/refresh', methods=['POST'])
def refresh():
    print("[INFO] Entered /refresh route")
    try:
        # result = refreshgcov.refresh_gcov(executor.ssh_client)
        result = refreshgcov.refresh_gcov(ssh_client)
        if result:
            print("[INFO] refresh_gcov completed successfully")
            return jsonify({'message': 'Refresh succeeded'})
        else:
            print("[ERROR] refresh_gcov returned False")
            return jsonify({'message': 'Refresh failed, see backend logs'})
    except Exception as e:
        print(f"[EXCEPTION] Exception occurred in /refresh: {e}")
        return jsonify({'message': 'Exception occurred, check logs'})

@app.route('/kernel/<path:subpath>')
def kernel_route(subpath):
    if subpath.endswith('.png') or subpath.endswith('.jpg') or subpath.endswith('.jpeg') or subpath.endswith('.gif') or subpath.endswith('.css'):
        static_path = os.path.join(app.root_path, 'templates/kernel')
        return send_from_directory(static_path, subpath)
    elif subpath.endswith('.html'):
        try:
            return render_template(f'kernel/{subpath}')
        except jinja2.TemplateNotFound:
            return "Template not found", 404
    else:
        abort(404)

@app.route('/user/<path:subpath>')
def user_route(subpath):
    if subpath.endswith('.png') or subpath.endswith('.jpg') or subpath.endswith('.jpeg') or subpath.endswith('.gif') or subpath.endswith('.css'):
        static_path = os.path.join(app.root_path, 'templates/user')
        return send_from_directory(static_path, subpath)
    elif subpath.endswith('.html'):
        try:
            return render_template(f'user/{subpath}')
        except jinja2.TemplateNotFound:
            return "Template not found", 404

    else:
        abort(404)



if __name__ == '__main__':

    ssh_client = ssh.ssh_get()

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host='0.0.0.0', port=5001, debug=False)

