from flask import Flask, request, send_file
from src.generator import generate_map

app = Flask(__name__)

@app.route('/generate_map', methods=['POST'])
def generate_map_endpoint():
    data = request.get_json()
    doc_text = data['content']

    map_file_path = generate_map(doc_text,1)
    return send_file(map_file_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(port=8080)


#run locally with python -m src.app and test with curl -X POST http://localhost:8080/generate_map \
    #  -H "Content-Type: application/json" \
    #  -d '{"content": "They went from Lok to Erendale in one day."}' \ 
    #  --output map.png

#python -m src.app
#ngrok http 8080