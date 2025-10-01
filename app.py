from flask import Flask, request, render_template_string
import gspread 
import os
import json
import tempfile 
import os # Necesario para limpiar el archivo temporal

app = Flask(__name__)

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---

# 1. Obtenemos la cadena de credenciales y la LIMPIAMOS
creds_json_string = os.environ.get('GOOGLE_CREDENTIALS')
if not creds_json_string:
    raise Exception("Error: La clave GOOGLE_CREDENTIALS no está configurada en Render.")

# EL CAMBIO CRÍTICO: Limpieza, Conversión y Reconstrucción del JSON (Soluciona el error de formato)
# ----------------------------------------------------
creds_json_string_cleaned = creds_json_string.strip() 

try:
    # 2. Convertimos la cadena limpia a bytes (encode) y la cargamos a JSON para validación
    creds_bytes = creds_json_string_cleaned.encode('utf-8') 
    GOOGLE_CREDS_OBJECT = json.loads(creds_bytes.decode('utf-8'))
    
    # 3. Compactamos el objeto JSON de vuelta a un string perfecto para el archivo temporal
    creds_json_string_final = json.dumps(GOOGLE_CREDS_OBJECT, separators=(',', ':'))
    
except Exception as e:
    # Si la cadena JSON es inválida, falla aquí y no genera el error extraño de gspread
    raise Exception(f"Error CRÍTICO al procesar la clave JSON: {e}")
# ----------------------------------------------------

# Nombres de la Hoja y Pestaña (Verificados por ti)
SHEET_NAME = "Hoja de cálculo sin título" 
WORKSHEET_NAME = "Hoja 1" 

# *******************************************************************
# RUTA 1: CARGA EL FORMULARIO (Maneja el QR)
# *******************************************************************
@app.route('/cargar_formulario', methods=['GET'])
def cargar_formulario():
    orden = request.args.get('orden', '')
    codigo = request.args.get('codigo', '')
    descripcion = request.args.get('descripcion', '') 
    lote = request.args.get('lote', '')             
    fecha_ini = request.args.get('fecha_ini', '')
    cantidad = request.args.get('cantidad', '')
    fecha_fin = request.args.get('fecha_fin', '')
    
    formulario_html = f"""
    <html>
    <head>
        <title>PROTOTIPO QR</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            input, button {{ width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; }}
            .read-only {{ background-color: #f0f0f0; }}
            .read-only-red {{ background-color: #ffcccc; }}
        </style>
    </head>
    <body>
        <h2> NOTIFICADOR ORDENES (Confirmación)</h2>
        <form method="POST" action="/guardar_datos_final">
            
            <label>1. No. Orden:</label>
            <input type="text" name="orden" value="{orden}" class="read-only-red" readonly>
            
            <label>2. Código:</label>
            <input type="text" name="codigo" value="{codigo}" class="read-only-red" readonly>
            
            <label>3. Descripción:</label>
            <input type="text" name="descripcion" value="{descripcion}" class="read-only" readonly>
            
            <label>4. Lote:</label>
            <input type="text" name="lote" value="{lote}" class="read-only" readonly>
            
            <hr style="border-top: 1px solid #ddd; margin: 20px 0;">
            
            <label>5. Fecha Inicial:</label>
            <input type="text" name="fecha_ini" value="{fecha_ini}" class="read-only" readonly>
            
            <label style="font-weight: bold; color: darkgreen;">6. Cantidad Programada (editable):</label>
            <input type="number" name="cantidad" value="{cantidad}">
            
            <label style="font-weight: bold; color: darkgreen;">7. Fecha Final (editable):</label>
            <input type="date" name="fecha_fin" value="{fecha_fin}">
            
            <button type="submit" style="background-color: #007bff; color: white; padding: 12px;"> PULSE PARA GUARDAR EN DATA BASE</button>
        </form>
        <p><small>RECUERDA QUE TODO ESTE BIEN.</small></p>
    </body>
    </html>
    """
    return render_template_string(formulario_html)


# *******************************************************************
# RUTA 2: GUARDA EN GOOGLE SHEETS
# *******************************************************************
@app.route('/guardar_datos_final', methods=['POST'])
def guardar_datos_final():
    
    # Creamos un archivo temporal para guardar las credenciales JSON limpias.
    tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    try:
        tmp.write(creds_json_string_final) # Escribimos el JSON que ya validamos y limpiamos.
        tmp.close()
        
        # 1. Obtener los datos del formulario 
        orden = request.form['orden']
        codigo = request.form['codigo']
        descripcion = request.form['descripcion'] 
        lote = request.form['lote']             
        fecha_ini = request.form['fecha_ini']
        cantidad = request.form['cantidad']
        fecha_fin = request.form['fecha_fin']
        
        datos_a_guardar = [orden, codigo, descripcion, lote, fecha_ini, cantidad, fecha_fin]

        # 2. Autenticación y Conexión a Google Sheets (Lee desde el archivo temporal)
        gc = gspread.service_account(filename=tmp.name)
        sh = gc.open(SHEET_NAME) 
        
        # 3. Seleccionar la Hoja de Trabajo (pestaña)
        ws = sh.worksheet(WORKSHEET_NAME) 

        # 4. Añadir la Fila 
        ws.append_row(datos_a_guardar)

        # 5. Respuesta de éxito
        return render_template_string(f"""
        <html>
        <body style="font-family: sans-serif; text-align: center; background-color: #ccffcc;">
            <h1 style="color: green;">Datos Guardados Correctamente</h1>
            <p>Orden <strong>{orden}</strong> registrada en Google Sheets.</p>
            <p><a href="https://docs.google.com/spreadsheets/d/{sh.id}/edit" target="_blank">VER DATOS EN GOOGLE SHEETS</a></p>
        </body>
        </html>
        """), 200

    except Exception as e:
        # En caso de error
        return render_template_string(f"""
        <html>
        <body style="font-family: sans-serif; text-align: center; background-color: #ffcccc;">
            <h1 style="color: red;">Error al Guardar los Datos</h1>
            <p>Verifique los logs de Render para detalles del error.</p>
            <p>Error: {str(e)}</p>
        </body>
        </html>
        """), 500
    finally:
        # 6. Asegura que el archivo temporal se borre después de usarlo.
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# La función home
@app.route('/')
def home():
    return "<h1>Servidor QR Activo. Usa /cargar_formulario para ver la app.</h1>"
