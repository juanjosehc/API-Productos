import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---

# Obtener la URL de la base de datos de las variables de entorno (Render provee 'DATABASE_URL')
# Fallback a SQLite local si no hay Postgres
database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_productos.db') 

# === CORRECCIÓN CLAVE PARA USAR PSYCOPG 3 ===
# Cambiamos 'postgres://' o 'postgresql://' a 'postgresql+psycopg://' 
# Esto le dice a SQLAlchemy que use el driver Psycopg 3.
if database_url and database_url.startswith("postgres://"):
    # Render usa 'postgres://', lo cambiamos al dialecto Psycopg 3
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url and database_url.startswith("postgresql://"):
    # Si la URL ya estaba en formato 'postgresql://', le agregamos el driver
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
# ============================================

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELO DE DATOS (TABLA) ---

class Producto(db.Model):
    __tablename__ = 'productos_no_perecederos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(50), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    # Fecha de ingreso del registro
    fecha_creacion = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        """Método auxiliar para convertir el objeto a diccionario JSON"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'marca': self.marca,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'stock': self.stock,
            'fecha_creacion': self.fecha_creacion
        }

# --- RUTAS DE LA API ---

@app.route('/')
def index():
    return jsonify({"mensaje": "API de Productos No Perecederos funcionando correctamente 🚀"})

# 1. Crear un nuevo producto (POST)
@app.route('/productos', methods=['POST'])
def crear_producto():
    data = request.get_json()

    # Validación simple
    if not data or 'nombre' not in data or 'precio' not in data:
        return jsonify({'error': 'Faltan datos obligatorios (nombre, precio)'}), 400

    nuevo_producto = Producto(
        nombre=data['nombre'],
        marca=data.get('marca', ''),
        descripcion=data.get('descripcion', ''),
        precio=data['precio'],
        stock=data.get('stock', 0)
    )

    try:
        db.session.add(nuevo_producto)
        db.session.commit()
        return jsonify({'mensaje': 'Producto creado', 'producto': nuevo_producto.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 2. Obtener todos los productos (GET)
@app.route('/productos', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()
    return jsonify([p.to_dict() for p in productos]), 200

# 3. Obtener un producto por ID (GET)
@app.route('/productos/<int:id>', methods=['GET'])
def obtener_producto_detalle(id):
    producto = Producto.query.get_or_404(id)
    return jsonify(producto.to_dict()), 200

# 4. Actualizar un producto (PUT)
@app.route('/productos/<int:id>', methods=['PUT'])
def actualizar_producto(id):
    producto = Producto.query.get_or_404(id)
    data = request.get_json()

    producto.nombre = data.get('nombre', producto.nombre)
    producto.marca = data.get('marca', producto.marca)
    producto.descripcion = data.get('descripcion', producto.descripcion)
    producto.precio = data.get('precio', producto.precio)
    producto.stock = data.get('stock', producto.stock)

    try:
        db.session.commit()
        return jsonify({'mensaje': 'Producto actualizado', 'producto': producto.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 5. Eliminar un producto (DELETE)
@app.route('/productos/<int:id>', methods=['DELETE'])
def eliminar_producto(id):
    producto = Producto.query.get_or_404(id)
    
    try:
        db.session.delete(producto)
        db.session.commit()
        return jsonify({'mensaje': 'Producto eliminado correctamente'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- INICIALIZACIÓN ---

# Crear tablas si no existen (se ejecuta al iniciar la app)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Obtiene el puerto asignado por Render (o usa 5000 por defecto para desarrollo local)
    port = int(os.environ.get('PORT', 5000)) 
    # Asegura que la aplicación escuche en todas las interfaces ('0.0.0.0')
    app.run(host='0.0.0.0', port=port)