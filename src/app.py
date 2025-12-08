#This file is for running the backend for the Google Docs plug-in. For local testing, use main.py.
from flask import Flask, request, jsonify
import base64
from src.generator import generate_map

app = Flask(__name__)

@app.route('/generate_map', methods=['POST'])
def generate_map_endpoint():
    data = request.get_json()
    doc_text = data['content']

    map_file_path, conflicts = generate_map(doc_text,1)
    with open(map_file_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')

    return jsonify({
        "map_png_base64": img_b64,
        "conflicts": conflicts
    })

if __name__ == '__main__':
    app.run(port=8080)


#run locally with 
# python -m src.app and test with:
# curl -X POST http://localhost:8080/generate_map \
    #  -H "Content-Type: application/json" \
    #  -d '{"content": "They went from Lok to Erendale in one day."}' \ 
    #  --output map.png

#run for Google Docs integration with:
# python -m src.app
#ngrok http 8080