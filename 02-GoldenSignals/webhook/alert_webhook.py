from flask import Flask, request
import datetime

app = Flask(__name__)

LOG_FILE = "/tmp/alertmanager.log"

@app.route('/webhook', methods=['POST'])
def webhook():
    alert = request.json
    now = datetime.datetime.now().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(f"{now} - Alerte reçue:\n{alert}\n\n")
    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
