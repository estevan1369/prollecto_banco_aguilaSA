import json
from flask import Flask, request, jsonify, render_template, session

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'  # Necesaria para usar session

ARCHIVO_DATOS = 'datos.json'
PIN_CORRECTO = '1234'  # PIN numérico como string
INTENTOS_MAX = 3

def cargar_datos():
    """Carga saldo e historial desde el archivo JSON."""
    try:
        with open(ARCHIVO_DATOS, 'r') as f:
            datos = json.load(f)
            return datos.get('saldo', 0), datos.get('historial', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, []

def guardar_datos(saldo, historial):
    """Guarda saldo e historial en el archivo JSON."""
    with open(ARCHIVO_DATOS, 'w') as f:
        json.dump({'saldo': saldo, 'historial': historial}, f, indent=4)

@app.route('/')
def index():
    """Sirve la página principal del cajero."""
    return render_template('index.html')

@app.route('/api/verificar_pin', methods=['POST'])
def verificar_pin():
    """Verifica el PIN ingresado. Inicia sesión si es correcto."""
    data = request.get_json()
    pin = data.get('pin', '')
    if pin == PIN_CORRECTO:
        session['autenticado'] = True
        session['intentos'] = 0
        # Cargar datos del usuario (para mantener consistencia)
        saldo, historial = cargar_datos()
        session['saldo'] = saldo
        session['historial'] = historial
        return jsonify({'success': True, 'mensaje': 'PIN correcto'})
    else:
        session['intentos'] = session.get('intentos', 0) + 1
        restantes = INTENTOS_MAX - session['intentos']
        if session['intentos'] >= INTENTOS_MAX:
            return jsonify({'success': False, 'bloqueado': True, 'mensaje': 'Demasiados intentos. Tarjeta bloqueada.'})
        else:
            return jsonify({'success': False, 'intentos_restantes': restantes, 'mensaje': f'PIN incorrecto. Intentos restantes: {restantes}'})

@app.route('/api/saldo', methods=['GET'])
def obtener_saldo():
    """Retorna el saldo actual (requiere autenticación)."""
    if not session.get('autenticado'):
        return jsonify({'error': 'No autenticado'}), 401
    saldo, _ = cargar_datos()
    session['saldo'] = saldo
    return jsonify({'saldo': saldo})

@app.route('/api/depositar', methods=['POST'])
def depositar():
    """Realiza un depósito con el 0.5% de interés (cobrado al usuario)."""
    if not session.get('autenticado'):
        return jsonify({'error': 'No autenticado'}), 401
    
    data = request.get_json()
    monto = float(data.get('monto', 0))
    num_cuenta = data.get('num_cuenta', '')
    
    if monto <= 0:
        return jsonify({'success': False, 'mensaje': 'El monto debe ser positivo.'})
    
    saldo, historial = cargar_datos()
    interes = monto * 0.005
    monto_neto = monto - interes
    saldo += monto_neto
    historial.append(f"+{monto_neto:.2f} depósito (cuenta {num_cuenta}, bruto {monto:.2f}, interés {interes:.2f})")
    guardar_datos(saldo, historial)
    session['saldo'] = saldo
    session['historial'] = historial
    
    return jsonify({
        'success': True,
        'saldo': saldo,
        'monto_neto': monto_neto,
        'interes': interes,
        'mensaje': f'Depósito exitoso. Neto ingresado: ${monto_neto:.2f} (se descontó 0.5% de interés)'
    })

@app.route('/api/retirar', methods=['POST'])
def retirar():
    """Realiza un retiro si hay saldo suficiente."""
    if not session.get('autenticado'):
        return jsonify({'error': 'No autenticado'}), 401
    
    data = request.get_json()
    monto = float(data.get('monto', 0))
    num_cuenta = data.get('num_cuenta', '')
    
    if monto <= 0:
        return jsonify({'success': False, 'mensaje': 'El monto debe ser positivo.'})
    
    saldo, historial = cargar_datos()
    if monto > saldo:
        return jsonify({'success': False, 'mensaje': 'Saldo insuficiente.'})
    
    saldo -= monto
    historial.append(f"-{monto:.2f} retiro (cuenta {num_cuenta})")
    guardar_datos(saldo, historial)
    session['saldo'] = saldo
    session['historial'] = historial
    
    return jsonify({
        'success': True,
        'saldo': saldo,
        'mensaje': f'Retiro de ${monto:.2f} exitoso.'
    })

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    """Retorna el historial completo de operaciones."""
    if not session.get('autenticado'):
        return jsonify({'error': 'No autenticado'}), 401
    
    _, historial = cargar_datos()
    return jsonify({'historial': historial})

@app.route('/api/salir', methods=['POST'])
def salir():
    """Cierra la sesión (simula expulsar tarjeta)."""
    session.clear()
    return jsonify({'success': True, 'mensaje': 'Sesión finalizada. Gracias por usar Banco Águila.'})

if __name__ == '__main__':
    app.run(debug=True, port=8000)