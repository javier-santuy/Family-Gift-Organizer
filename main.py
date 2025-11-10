from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func # Necesario para la función max()
import os 

# --- Configuración de la Aplicación y la Base de Datos ---
app = Flask(__name__)

# Configuración de SQLAlchemy: Usa una base de datos SQLite en un archivo llamado 'regalos.db'
# ESTO ES UN ARCHIVO LOCAL Y FUNCIONA SOLO PARA DESARROLLO.
# Para despliegue en Render, esta línea se cambiaría por una URL de PostgreSQL.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///regalos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelo de la Base de Datos ---
class Regalo(db.Model):
    # La tabla se llama 'regalo'
    id = db.Column(db.Integer, primary_key=True)
    destinatario = db.Column(db.String(80), nullable=False)
    encargado = db.Column(db.String(80), nullable=False)
    regalo = db.Column(db.String(120), nullable=False)
    costo = db.Column(db.Float, default=0.00)
    estado = db.Column(db.String(50), default='Pendiente') # Ejemplo: 'Pendiente', 'Comprado'
    
    def __repr__(self):
        return f'<Regalo {self.id}: {self.regalo}>'

# --- Variables Globales (SOLO las que no van en la DB) ---
PARTICIPANTES = ['Juan Antonio', 'Elisa', 'David', 'Andrea', 'Alba', 'Javier', 'Pablo(Alba)', 'Pablo(Andrea)', 'Sara', 'Nura', 'Anaiet', "Ale"] 
USUARIO_ACTUAL = None
# ------------------------------------------------

# --- Funciones Auxiliares ---

@app.before_request
def create_tables():
    """Crea la base de datos y la tabla si no existen."""
    db.create_all()

# --- RUTAS EXISTENTES ---

@app.route('/', methods=['GET', 'POST'])
def login():
    global USUARIO_ACTUAL
    error = None
    if request.method == 'POST':
        USUARIO_ACTUAL = request.form.get('nombre')
        if USUARIO_ACTUAL in PARTICIPANTES:
            return redirect(url_for('ver_regalos'))
        else:
            error = "Usuario no válido"
    
    return render_template('login.html', participantes=PARTICIPANTES, error=error)

@app.route('/regalos')
def ver_regalos():
    global USUARIO_ACTUAL
    if not USUARIO_ACTUAL:
        return redirect(url_for('login'))
        
    # 1. Obtener el filtro de la URL (si existe)
    filtro_persona = request.args.get('persona') 
    
    # 2. Construir la consulta base: Excluir regalos para el usuario actual
    consulta_base = Regalo.query.filter(Regalo.destinatario != USUARIO_ACTUAL)
    
    # 3. Aplicar el filtro de destinatario si se especificó uno
    if filtro_persona:
        regalos_visibles = consulta_base.filter(Regalo.destinatario == filtro_persona).all()
    else:
        regalos_visibles = consulta_base.all()
    
    return render_template('regalos.html', 
                            usuario=USUARIO_ACTUAL, 
                            participantes=PARTICIPANTES,
                            regalos=regalos_visibles)

@app.route('/logout')
def logout():
    global USUARIO_ACTUAL
    USUARIO_ACTUAL = None
    return redirect(url_for('login'))

# --- 🎁 RUTAS DE FUNCIONALIDAD 🎁 ---

@app.route('/agregar', methods=['POST'])
def agregar_regalo():
    global USUARIO_ACTUAL
    if not USUARIO_ACTUAL:
        return redirect(url_for('login'))

    try:
        costo_float = round(float(request.form['costo']), 2)
    except ValueError:
        costo_float = 0.00

    # Crear una nueva instancia del modelo Regalo
    nuevo_regalo = Regalo(
        destinatario=request.form['destinatario'],
        encargado=request.form['encargado'],
        regalo=request.form['regalo'],
        costo=costo_float,
        estado=request.form['estado']
    )

    # Añadir a la sesión y hacer COMMIT para guardar en la base de datos
    db.session.add(nuevo_regalo)
    db.session.commit()
    
    return redirect(url_for('ver_regalos'))

@app.route('/borrar/<int:regalo_id>', methods=['POST'])
def borrar_regalo(regalo_id):
    global USUARIO_ACTUAL
    if not USUARIO_ACTUAL:
        return redirect(url_for('login'))
        
    # Encontrar el regalo por ID
    regalo = Regalo.query.get_or_404(regalo_id)
    
    # Regla: No se puede borrar si es para el usuario actual
    if regalo.destinatario == USUARIO_ACTUAL:
        return "Error: No puedes borrar un regalo destinado a ti.", 403 
        
    # Borrar y hacer COMMIT
    db.session.delete(regalo)
    db.session.commit()
    
    return redirect(url_for('ver_regalos'))

@app.route('/modificar/<int:regalo_id>', methods=['GET', 'POST'])
def modificar_regalo(regalo_id):
    global USUARIO_ACTUAL
    if not USUARIO_ACTUAL:
        return redirect(url_for('login'))
        
    # Encontrar el regalo por ID
    regalo = Regalo.query.get_or_404(regalo_id)

    # Regla: Permite modificar si NO es para el usuario actual
    if regalo.destinatario == USUARIO_ACTUAL:
        return "Error: No puedes modificar un regalo destinado a ti.", 403 
    
    estados_posibles = ['Pendiente', 'Comprado', 'Envuelto', 'Entregado']
    
    if request.method == 'POST':
        # Actualizar los datos del objeto (la sesión de DB los detecta)
        regalo.destinatario = request.form['destinatario']
        regalo.encargado = request.form['encargado'] 
        regalo.regalo = request.form['regalo']
        
        try:
            regalo.costo = round(float(request.form['costo']), 2)
        except ValueError:
            pass
            
        regalo.estado = request.form['estado']
        
        # Guardar los cambios en la base de datos
        db.session.commit()
        
        return redirect(url_for('ver_regalos'))
    
    # Si es GET, mostrar el formulario de modificación
    return render_template('modificar.html', 
                            regalo=regalo, 
                            participantes=PARTICIPANTES,
                            estados=estados_posibles)

if __name__ == '__main__':
    # Usamos 127.0.0.1 para que se ejecute correctamente en el entorno de desarrollo
    # Es recomendable ejecutar Python en la consola con 'python main.py' o 'flask run'
    with app.app_context():
        # Crea las tablas si no existen antes de ejecutar la app
        db.create_all()
    app.run(host='127.0.0.1', debug=True)