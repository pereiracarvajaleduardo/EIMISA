import os
import shutil
import hashlib
import csv
import re
import fitz  # PyMuPDF para mejor extracción de texto
from PyPDF2 import PdfReader

# 🔹 Rutas base del proyecto
RUTA_BASE = os.path.join(os.getcwd(), "k484")
RUTA_ENTRADA = os.path.join(RUTA_BASE, "entrada")
RUTA_NO_CLASIFICADOS = os.path.join(RUTA_BASE, "no_clasificados")
RUTA_LOG = os.path.join(RUTA_BASE, "clasificacion_log.csv")

# 🔹 Palabras clave principales
CARPETAS_PRINCIPALES = ["wsa", "sws", "tk"]

# 🔹 Crear estructura de carpetas
def crear_estructura_base():
    os.makedirs(RUTA_ENTRADA, exist_ok=True)
    os.makedirs(RUTA_NO_CLASIFICADOS, exist_ok=True)
    for principal in CARPETAS_PRINCIPALES:
        os.makedirs(os.path.join(RUTA_BASE, principal), exist_ok=True)
    os.makedirs(os.path.join(RUTA_BASE, "duplicados"), exist_ok=True)

# 🔹 Extraer texto de la esquina inferior izquierda del PDF
def leer_pdf(path):
    try:
        doc = fitz.open(path)
        texto = ""

        for page in doc.pages[:3]:  # Solo primeras 3 páginas
            rectangulo = fitz.Rect(50, page.mediabox[3] - 200, 300, page.mediabox[3] - 50)  
            texto_sector = page.get_text("text", clip=rectangulo) or ""
            texto += texto_sector.lower()

        return texto
    except Exception as e:
        print(f"Error leyendo {path}: {e}")
        return ""

# 🔹 Calcular hash del archivo
def calcular_hash(path):
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# 🔹 Guardar log de clasificación
def guardar_log(nombre, origen, destino, estado, palabras):
    existe = os.path.exists(RUTA_LOG)
    with open(RUTA_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["Archivo", "Origen", "Destino", "Estado", "Palabras clave"])
        writer.writerow([nombre, origen, destino, estado, ", ".join(palabras)])

# 🔹 Clasificar PDF según contenido
def clasificar_pdf(nombre_archivo):
    ruta_pdf = os.path.join(RUTA_ENTRADA, nombre_archivo)
    if not os.path.exists(ruta_pdf):
        print(f"❌ Archivo no encontrado: {ruta_pdf}")
        return

    contenido = leer_pdf(ruta_pdf)
    hash_archivo = calcular_hash(ruta_pdf)

    # 🔹 Buscar duplicados
    for root, _, files in os.walk(RUTA_BASE):
        for file in files:
            if file.endswith(".pdf"):
                path_existente = os.path.join(root, file)
                if path_existente != ruta_pdf and calcular_hash(path_existente) == hash_archivo:
                    print(f"⚠️ Duplicado detectado y sustituido: {nombre_archivo}")
                    mover_y_reemplazar(ruta_pdf, path_existente)
                    guardar_log(nombre_archivo, ruta_pdf, path_existente, "duplicado-sustituido", [])
                    return

    palabras_clave_detectadas = []
    destino = None

    # 🔹 Detectar palabras clave principales
    destino_principal = next((key for key in CARPETAS_PRINCIPALES if key in contenido), None)
    
    # 🔹 Buscar código específico (C-3808)
    codigo_match = re.search(r"C[-\s]?3808", contenido)

    if destino_principal and codigo_match:
        subcarpeta_cod = "C-3808"
        destino = os.path.join(RUTA_BASE, destino_principal, subcarpeta_cod)
        palabras_clave_detectadas = [destino_principal, subcarpeta_cod]
    else:
        destino = RUTA_NO_CLASIFICADOS
        palabras_clave_detectadas = ["no_clasificado"]

    os.makedirs(destino, exist_ok=True)
    mover_y_reemplazar(ruta_pdf, os.path.join(destino, nombre_archivo))
    guardar_log(nombre_archivo, ruta_pdf, destino, "clasificado", palabras_clave_detectadas)

# 🔹 Mover archivo con reemplazo si existe
def mover_y_reemplazar(src, dst):
    if os.path.abspath(src) == os.path.abspath(dst):
        print(f"⚠️ Archivo ya está en la ubicación correcta: {dst}")
        return

    if os.path.exists(dst):
        os.remove(dst)

    if os.path.exists(src):
        try:
            shutil.move(src, dst)
            print(f"✔️ Movido a: {dst}")
        except FileNotFoundError:
            print(f"❌ No se pudo mover. Archivo no encontrado: {src}")
    else:
        print(f"❌ Archivo de origen no encontrado: {src}")

# 🔹 Ejecutar clasificación
def main():
    crear_estructura_base()
    archivos = [f for f in os.listdir(RUTA_ENTRADA) if f.lower().endswith(".pdf")]
    for archivo in archivos:
        print(f"📄 Analizando: {archivo}")
        clasificar_pdf(archivo)

if __name__ == "__main__":
    main()