# user will highlight a word and click "send to server"
# if there are mutliple forms, browser will show a poup with the different forms and prompts for which ones to send
from flask import Flask, request
import subprocess
import os
import signal
import time, db
import inflection as iad

app = Flask(__name__)

env = os.environ.copy()
env['SYNC_USER1'] = 'user:pass'
process = subprocess.Popen(['python', '-m', 'anki.syncserver'], env=env)
def parseToHumanString(parse):
  return f'{parse.word}: {", ".join(parse.tag.grammemes)}'

def tooManyBasesResponse(baseWordParses):
  return '\n'.join(["too many"] + [parseToHumanString(p) for p in baseWordParses])

@app.route('/', methods=['GET'])
def test():
  return 'test'

@app.route('/add/<word>', methods=['GET'])
def endpoint(word):
  global process
  grammemeString = request.args.get('grammemes', '')
  print(f"{(word + ' ' + grammemeString)}")
  status, result = iad.getAllInflections(word, grammemeString)
  if not status:
    return tooManyBasesResponse(result)

  os.killpg(os.getpgid(process.pid), signal.SIGINT)
  db.addToDB(result)
  process = subprocess.Popen(['python3', '-m', 'anki.syncserver'], env=env)
  return "success"

if __name__ == '__main__':
  app.run(host="0.0.0.0", port=81)