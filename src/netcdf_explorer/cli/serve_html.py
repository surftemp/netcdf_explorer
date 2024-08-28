# MIT License
#
# Copyright (C) 2023-2024 National Centre For Earth Observation (NCEO)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import io
import logging
import sys
import json

from flask import Flask, render_template, request, send_from_directory, abort, jsonify, send_file

from .apply_labels import apply_labels

global folder

# flask initialisation and configuration (see config.py)
app = Flask(__name__)

labels_path = None
labels = None
labels_updated = False

class App:
    """
    Define the routes and handlers for the web service
    """

    logger = logging.getLogger("app")

    def __init__(self):
        pass

    @staticmethod
    @app.route('/', methods=['GET'])
    @app.route('/index.html', methods=['GET'])
    def fetch_index():
        return send_from_directory(folder, 'index.html')

    @staticmethod
    @app.route('/<string:path>', methods=['GET'])
    def fetch(path):
        return send_from_directory(folder, path)

    @staticmethod
    @app.route('/data/<string:path>', methods=['GET'])
    def fetch_data(path):
        with open(os.path.join(folder, "data", path),"rb") as f:
            return send_file(io.BytesIO(f.read()),mimetype="application/binary")

    @staticmethod
    @app.route('/images/<string:path>', methods=['GET'])
    def fetch_images(path):
        return send_from_directory(folder + "/images", path)

    @staticmethod
    @app.route('/service_info/services.json', methods=['GET'])
    def service_info():
        return jsonify(labels=True)

    @staticmethod
    @app.route('/label/<string:label_group>/<int:index>/<string:label>', methods=['POST'])
    def update_label(label_group, index, label):
        print(label_group, index, label)
        labels["values"][label_group][index] = label
        global labels_updated
        labels_updated = True
        resp = jsonify(success=True)
        return resp

import signal

class SignalHandler:

  def __init__(self):
      signal.signal(signal.SIGINT, self.save_on_exit)
      signal.signal(signal.SIGTERM, self.save_on_exit)

  def save_on_exit(self, signum, frame):
      if labels_updated:
          print(f"Saving {labels_path}")
          with open(labels_path,"w") as f:
              f.write(json.dumps(labels,indent=4))
          if "netcdf_filename" in labels:
              netcdf_path = os.path.join(folder,labels["netcdf_filename"])
              print(f"Saving {netcdf_path}")
              apply_labels(labels_path,netcdf_path)
      sys.exit(0)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=9009)
    parser.add_argument("--folder", type=str, default=".")
    args = parser.parse_args()
    folder=args.folder

    labels_path = os.path.join(folder, "labels.json")
    labels = None
    if os.path.exists(labels_path):
        with open(labels_path) as f:
            labels = json.loads(f.read())
            print("Loaded labels...")

    gk = SignalHandler()
    app.run(host=args.host, port=args.port)


