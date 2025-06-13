from flask import Flask, jsonify
from threading import Thread
from modules import airtable

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

@app.route('/status')
def status():
    records = airtable.fetch_records().json().get('records', [])
    result = []
    for rec in records:
        f = rec['fields']
        result.append({
            'Device': f.get('Device ID'),
            'Status': f.get('Status'),
            'Remaining': f.get('Next Test (hours)', 'N/A'),
            'Expected End': f.get('Expected End')
        })
    return jsonify(result)

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()
