import sqlite3
import json
from operator import attrgetter
from time import time

def formatData(formatCommaDataPair):
  return '\x1f'.join('\x1f'.join(map(attrgetter('data'), formatCommaDataPair)))

def addToDB(formatCommaDataPair):
  conn = sqlite3.connect('~/.syncserver/user/collection.anki2')
  cur = conn.cursor()

  def createNoteType(models, formatIdentifier, fields):
    print('in createnotetype')
    cur.execute("SELECT models FROM col")
    modelId = int(time())
    fieldsSplit = fields.split(',')
    models[modelId] = {
      "name": formatIdentifier,
      "usn": -1,
      "type": 0,
      "fields": [{"ord": 0, "name": 'base'}] + [{"ord": ord, "name": name} for ord, name in enumerate(fieldsSplit, start=1)],
      "tmpls": [{
        "name": formatIdentifier,
        "qfmt": "{{base}}",
        "afmt": f"{{{{{fieldsSplit[0]}}}}}",
        "ord": 0
      }]
    }
    cur.execute("UPDATE col SET models = ?", (json.dumps(models),))

    print(f'{models=}')
    return str(modelId)

  def addNote(modelId, data):
    print('in addNote')
    noteId = int(time() * 1000)
    mod = noteId / 1000
    cur.execute("""
        INSERT INTO notes (id, guid, mid, mod, usn, tags, flds)
        VALUES (?, ?, ?, ?, -1, '', ?)
    """, (noteId, str(noteId), modelId, mod, data))
    cur.execute("""
        INSERT INTO cards (nid, did, ord, mod, usn, type, queue)
        VALUES (?, ?, 0, ?, -1, 0, 0)
    """, (noteId, modelId, mod))
  
  def addToDB(formatCommaDataPair):
    formats = map(attrgetter('format'), formatCommaDataPair)
    formatIdentifier = ','.join(','.join(format) for format in formats)
    status, result = getModelId(formatIdentifier)
    if status:
      modelId = result
    else:
      modelId = createNoteType(result, formatIdentifier, format)
    print(f'{modelId=}')
    #modelId = result if status else createNoteType(result, formatIdentifier, format)
    addNote(modelId, map(attrgetter('data'), formatData(formatCommaDataPair)))
    
  def getModelId(formatIdentifier):
    cur.execute("SELECT models FROM col")
    models_json = cur.fetchone()[0]
    models = json.loads(models_json)
    for model_id, model in models.items():
        if model['name'] == formatIdentifier:
            return True, model_id
    return False, models
  
  def closeConnection():
    conn.commit()
    conn.close()

  
  print(f'{addToDB(formatCommaDataPair)=}')
  #closeConnection()
  conn.close()