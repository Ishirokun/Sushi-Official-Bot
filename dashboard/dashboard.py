import logging
from flask import Flask, render_template
from threading import Thread


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


app = Flask('')


@app.route('/')
def home():
  return render_template("index.html")


def run():
  app.run(host='0.0.0.0', port=8080)


def awoken():
  t=Thread(target=run)
  t.start()