from flask import Flask, request, jsonify, send_file, render_template_string
import os
import sqlite3
import datetime
import fitz  # PyMuPDF
from nltk.tokenize import TreebankWordTokenizer

app = Flask(__name__)
FOLDER_PATH = "./k484"
tokenizer = TreebankWordTokenizer()

# 🔹 Inicializar base de datos
def init_db():
    conn = sqlite3.connect("search_history.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS history (query TEXT, timestamp TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS index_pdf (file_path TEXT PRIMARY KEY, content TEXT)")
    conn.commit()
    conn.close()

init_db()

# 🔹 Limpiar el índice de archivos eliminados
def clean_index():
    conn = sqlite3.connect("search_history.db")
    c = conn.cursor()
    c.execute("SELECT file_path FROM index_pdf")
    rows = c.fetchall()
    for (file_path,) in rows:
        full_path = os.path.join(FOLDER_PATH, file_path)
        if not os.path.exists(full_path):
            c.execute("DELETE FROM index_pdf WHERE file_path=?", (file_path,))
    conn.commit()
    conn.close()

clean_index()

# 🔹 Indexar PDFs (solo zona inferior izquierda)
def index_pdfs():
    conn = sqlite3.connect("search_history.db")
    c = conn.cursor()

    for root, _, files in os.walk(FOLDER_PATH):
        for file in files:
            if not file.lower().endswith('.pdf'):
                continue

            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, FOLDER_PATH)

            c.execute("SELECT file_path FROM index_pdf WHERE file_path=?", (relative_path,))
            if c.fetchone():
                continue

            try:
                with fitz.open(full_path) as doc:
                    extracted = []
                    for page in doc[:3]:
                        rect = page.rect
                        width, height = rect.width, rect.height
                        lower_left = fitz.Rect(0, height * 0.6, width * 0.4, height)
                        text = page.get_text("text", clip=lower_left)
                        extracted.append(text)
                    content = " ".join(extracted)
                    c.execute("INSERT INTO index_pdf VALUES (?, ?)", (relative_path, content.lower()))
            except Exception as e:
                print(f"Error al indexar {file}: {e}")

    conn.commit()
    conn.close()

index_pdfs()

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>k484 - Buscador de PDF</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f4f4f4; }
            .dark-mode { background: #2b2b2b; color: white; }
            input[type="text"] { width: 300px; padding: 5px; }
            button { padding: 6px 10px; }
            ul { list-style: none; padding: 0; margin-top: 20px; }
            li { margin: 5px 0; }
            a { text-decoration: none; color: blue; }
            .logo { font-size: 20px; font-weight: bold; color: #333; }
        </style>
    </head>
    <body>
        <div class="logo">EIMISA ACONCAGUA</div>
        <h1>📁 k484</h1>
        <button onclick="toggleDarkMode()">Modo Oscuro</button>
        <input type="text" id="searchInput" placeholder="Buscar archivos..." onkeyup="getSuggestions()">
        <button onclick="performSearch()">Buscar</button>

        <h3>Sugerencias:</h3>
        <ul id="suggestions"></ul>

        <h3>Resultados:</h3>
        <ul id="results"></ul>

        <script>
            function toggleDarkMode() {
                document.body.classList.toggle('dark-mode');
            }

            function getSuggestions() {
                const query = document.getElementById('searchInput').value;
                fetch('/suggestions?q=' + encodeURIComponent(query))
                    .then(response => response.json())
                    .then(data => {
                        const suggestionsList = document.getElementById('suggestions');
                        suggestionsList.innerHTML = '';
                        data.forEach(suggestion => {
                            const item = document.createElement('li');
                            item.innerText = suggestion;
                            item.onclick = () => {
                                document.getElementById('searchInput').value = suggestion;
                                performSearch();
                            };
                            suggestionsList.appendChild(item);
                        });
                    });
            }

            function performSearch() {
                const query = document.getElementById('searchInput').value;
                fetch('/search?q=' + encodeURIComponent(query))
                    .then(response => response.json())
                    .then(data => {
                        const results = document.getElementById('results');
                        results.innerHTML = '';

                        if (Object.keys(data).length === 0) {
                            results.innerHTML = '<li>No se encontraron resultados.</li>';
                        } else {
                            for (const folder in data) {
                                const folderItem = document.createElement('li');
                                folderItem.innerHTML = `<strong>📂 ${folder}</strong>`;
                                results.appendChild(folderItem);

                                const fileList = document.createElement('ul');
                                data[folder].forEach(fileInfo => {
                                    const item = document.createElement('li');
                                    const link = document.createElement('a');
                                    link.href = '/view/' + fileInfo["ruta"];
                                    link.target = '_blank';
                                    link.innerText = fileInfo["archivo"];
                                    item.appendChild(link);
                                    fileList.appendChild(item);
                                });

                                results.appendChild(fileList);
                            }
                        }
                    })
                    .catch(error => console.error('Error en la búsqueda:', error));
            }
        </script>
    </body>
    </html>
    """)

@app.route('/search')
def search_files():
    query = request.args.get('q', '').lower()
    query_tokens = tokenizer.tokenize(query) if query else []

    conn = sqlite3.connect("search_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO history VALUES (?, ?)", (query, str(datetime.datetime.now())))
    conn.commit()

    matching_files = {}
    c.execute("SELECT file_path, content FROM index_pdf")
    for file_path, content in c.fetchall():
        full_path = os.path.join(FOLDER_PATH, file_path)
        folder = os.path.dirname(file_path) or "Raíz"

        found = any(token in content for token in query_tokens) or \
                any(token in os.path.basename(file_path).lower() for token in query_tokens)

        if found:
            if folder not in matching_files:
                matching_files[folder] = []
            matching_files[folder].append({"archivo": os.path.basename(file_path), "ruta": file_path})

    conn.close()
    return jsonify(matching_files)

@app.route('/suggestions')
def get_suggestions():
    query = request.args.get('q', '').lower()
    conn = sqlite3.connect("search_history.db")
    c = conn.cursor()

    suggestions = set()
    c.execute("SELECT query FROM history WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 10", ('%' + query + '%',))
    suggestions.update(row[0] for row in c.fetchall())

    c.execute("SELECT content FROM index_pdf")
    for (content,) in c.fetchall():
        for word in content.split():
            if query in word:
                suggestions.add(word)
            if len(suggestions) >= 10:
                break
        if len(suggestions) >= 10:
            break

    conn.close()
    return jsonify(list(suggestions)[:10])

@app.route('/view/<path:filename>')
def view_pdf(filename):
    full_path = os.path.join(FOLDER_PATH, filename)
    if not os.path.exists(full_path):
        print("NO ENCONTRADO:", full_path)
        return "Archivo no encontrado", 404
    return send_file(full_path, mimetype='application/pdf', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
