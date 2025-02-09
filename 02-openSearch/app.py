from flask import Flask, jsonify, request
import random, logging
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

# Configuration du logger JSON
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(pathname)s %(funcName)s %(lineno)d')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

@app.route('/status')
def status():
    user_id = request.args.get("user_id", "unknown")
    if random.random() < 0.1:  # Simule 10% d'erreurs
        logger.error(f"Request failed for user_id={user_id}")
        return jsonify({"message": "Error"}), 500
    else:
        logger.info(f"Request successful for user_id={user_id}")
        return jsonify({"message": "OK"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
