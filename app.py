from flask import Flask, request, render_template_string
import gspread 
import os
import json
import tempfile 

app = Flask(__name__)

# --- CONFIGURACIÓN DE GOOGLE SHEETS (CON CONVERSIÓN FORZADA A BYTES) ---

# 1. Obtenemos la cadena de credenciales desde Render
creds_json_string = os.environ.get('GOOGLE_CREDENTIALS')
if not creds_json_string:
    raise Exception("Error: La clave GOOGLE_CREDENTIALS no está configurada en Render.")

# Solución para 'Cannot convert str to a seekable bit stream' (Limpieza y Compactación)
# ----------------------------------------------------
creds_json_string_cleaned = creds_json_string.strip() 

try:
    # 2. Convertimos la cadena limpia a bytes, la cargamos como objeto y la compactamos
    creds_bytes = creds_json_string_cleaned.encode('utf-8') 
    GOOGLE_CREDS_OBJECT = json.loads(creds_bytes.decode('utf-8'))
    # Genera el JSON limpio y compacto que se escribirá en el archivo temporal
    creds_json_string_final = json.dumps(GOOGLE_CREDS_OBJECT, separators=(',', ':'))
    
except Exception as e:
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
        <title>NOTIFICADOR QR</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            /* ESTILO SUPER COOL Y MODERNO */
            body {{ 
                font-family: 'Arial', sans-serif; 
                background-color: #f4f7f6; 
                padding: 10px; 
                color: #333;
            }}
            .container {{
                max-width: 450px;
                margin: 20px auto;
                padding: 20px;
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
            }}
            h2 {{
                color: #007bff;
                text-align: center;
                margin-bottom: 25px;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }}
            label {{
                display: block;
                margin-top: 15px;
                margin-bottom: 5px;
                font-weight: bold;
                font-size: 0.95em;
            }}
            input[type="text"], input[type="number"], input[type="date"] {{
                width: 100%;
                padding: 12px;
                margin: 5px 0 15px 0;
                display: inline-block;
                border: 1px solid #ccc;
                border-radius: 6px;
                box-sizing: border-box;
                font-size: 1em;
                transition: border-color 0.3s;
            }}
            input:focus {{
                border-color: #007bff;
                outline: none;
            }}
            /* Estilos para campos de solo lectura */
            .read-only {{ 
                background-color: #e9ecef; 
                color: #495057;
                border: 1px solid #ced4da;
            }}
            .read-only-red {{ 
                background-color: #f8d7da; /* Fondo suave rojo */
                color: #721c24; /* Texto rojo oscuro */
                border: 1px solid #f5c6cb;
            }}
            /* Estilo del botón */
            button[type="submit"] {{
                background-color: #28a745; /* Verde fuerte para Guardar */
                color: white;
                padding: 14px 20px;
                margin-top: 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1.1em;
                font-weight: bold;
                transition: background-color 0.3s, transform 0.1s;
            }}
            button[type="submit"]:hover {{
                background-color: #218838;
                transform: translateY(-1px);
            }}
            hr {{
                border: 0;
                border-top: 1px solid #ddd;
                margin: 25px 0;
            }}
            .editable-label {{
                color: #007bff; /* Azul para resaltar lo editable */
            }}

        </style>
    </head>
    <body>
        <div class="container">
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
                
                <hr>
                
                <label>5. Fecha Inicial (Registro):</label>
                <input type="text" name="fecha_ini" value="{fecha_ini}" class="read-only" readonly>
                
                <label class="editable-label">6. Cantidad Programada (editable):</label>
                <input type="number" name="cantidad" value="{cantidad}" required>
                
                <label class="editable-label">7. Fecha Final (editable):</label>
                <input type="date" name="fecha_fin" value="{fecha_fin}" required>
                
                <button type="submit"> PULSE PARA GUARDAR EN DATA BASE</button>
            </form>
            <p style="text-align: center; margin-top: 20px;"><small>Verifique la información antes de guardar.</small></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(formulario_html)


# *******************************************************************
# RUTA 2: GUARDA EN GOOGLE SHEETS
# *******************************************************************
@app.route('/guardar_datos_final', methods=['POST'])
def guardar_datos_final():
    
    # Creamos un archivo temporal, pero ahora usamos el JSON ya validado y limpio
    tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    try:
        # Escribimos el JSON que ya limpiamos y compactamos
        tmp.write(creds_json_string_final) # <-- USA EL JSON COMPACTADO Y LIMPIO
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
        # ESTO RESUELVE EL ERROR 'Invalid JWT Signature' AL USAR UNA CLAVE NUEVA
        gc = gspread.service_account(filename=tmp.name)
        sh = gc.open(SHEET_NAME) 
        
        # 3. Seleccionar la Hoja de Trabajo (pestaña)
        ws = sh.worksheet(WORKSHEET_NAME) 

        # 4. Añadir la Fila 
        ws.append_row(datos_a_guardar)

        # 5. Respuesta de éxito (también con estilo mejorado)
        return render_template_string(f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; text-align: center; background-color: #e6ffe6; padding: 50px; }}
                .message-box {{ max-width: 400px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; border: 3px solid #28a745; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #28a745; }}
                p {{ color: #333; }}
                a {{ color: #007bff; text-decoration: none; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="message-box">
                <h1>✅ Datos Guardados Correctamente</h1>
                <p>Orden <strong>{orden}</strong> registrada en Google Sheets.</p>
                <p><a href="https://docs.google.com/spreadsheets/d/{sh.id}/edit" target="_blank">VER DATOS EN GOOGLE SHEETS</a></p>
                <p style="margin-top: 20px;"><a href="/">Volver al inicio</a></p>
            </div>
        </body>
        </html>
        """), 200

    except Exception as e:
        # En caso de error (también con estilo mejorado)
        return render_template_string(f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; text-align: center; background-color: #ffe6e6; padding: 50px; }}
                .message-box {{ max-width: 450px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; border: 3px solid #dc3545; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #dc3545; }}
                p {{ color: #333; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <div class="message-box">
                <h1>❌ Error al Guardar los Datos</h1>
                <p>Verifique los logs de Render para detalles del error.</p>
                <p style="font-size: 0.9em; margin-top: 20px; padding: 10px; border: 1px solid #f5c6cb; background-color: #f8d7da;">
                    <strong>Error:</strong> {str(e)}
                </p>
            </div>
        </body>
        </html>
        """), 500
    finally:
        # 6. Asegura que el archivo temporal se borre después de usarlo.
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


# RUTA PRINCIPAL
@app.route('/')
def home():
    return "<h1>Servidor QR Activo. Usa /cargar_formulario para ver la app.</h1>"
