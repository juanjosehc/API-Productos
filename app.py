import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---

# Obtener la URL de la base de datos de las variables de entorno (Render provee 'DATABASE_URL')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///local_logistica.db') 

# Corrección para usar el driver Psycopg 3 (psycopg) con PostgreSQL en SQLAlchemy
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DE DATOS ---

class Usuario(db.Model):
    __tablename__ = 'usuarios_acceso'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    rol = db.Column(db.String(50), nullable=False) # Ej: Vendedor, Repartidor, Admin
    fecha_creacion = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'email': self.email,
            'rol': self.rol,
            'fecha_creacion': self.fecha_creacion
        }

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    direccion_entrega = db.Column(db.String(255), nullable=False)
    vendedor = db.Column(db.String(100), nullable=True) # Nombre del vendedor (puede ser un ID de usuario)
    fecha_pedido = db.Column(db.DateTime(timezone=True), server_default=func.now())
    fecha_entrega_estimada = db.Column(db.Date, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre_cliente': self.nombre_cliente,
            'telefono': self.telefono,
            'direccion_entrega': self.direccion_entrega,
            'vendedor': self.vendedor,
            'fecha_pedido': self.fecha_pedido,
            'fecha_entrega_estimada': str(self.fecha_entrega_estimada) if self.fecha_entrega_estimada else None
        }

class Ruta(db.Model):
    __tablename__ = 'rutas_logistica'

    id = db.Column(db.Integer, primary_key=True)
    nombre_ruta = db.Column(db.String(100), nullable=False)
    zona_asignada = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    numero_tiendas_asignadas = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'nombre_ruta': self.nombre_ruta,
            'zona_asignada': self.zona_asignada,
            'descripcion': self.descripcion,
            'numero_tiendas_asignadas': self.numero_tiendas_asignadas,
            'fecha_creacion': self.fecha_creacion
        }

# --- RUTAS CRUD GENÉRICAS ---

def create_crud_routes(app, model, endpoint, required_fields):
    """
    Función para generar rutas CRUD estándar para un modelo dado.
    """
    
    # RUTA BASE: LISTAR y CREAR
    @app.route(f'/{endpoint}', methods=['GET', 'POST'])
    def handle_items():
        if request.method == 'GET':
            items = model.query.all()
            return jsonify([item.to_dict() for item in items]), 200

        elif request.method == 'POST':
            data = request.get_json()
            
            # Validación de campos requeridos
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'El campo "{field}" es obligatorio'}), 400
            
            try:
                # Creación dinámica de la instancia del modelo
                # Nota: Esto asume que los nombres de los campos en el JSON coinciden con los del modelo.
                new_item = model(**{k: v for k, v in data.items() if hasattr(model, k)})
                
                db.session.add(new_item)
                db.session.commit()
                return jsonify({'mensaje': f'{model.__name__} creado', endpoint: new_item.to_dict()}), 201
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error al crear {model.__name__}: {e}")
                return jsonify({'error': f'Error interno al guardar: {str(e)}'}), 500

    # RUTAS ID: OBTENER, ACTUALIZAR y ELIMINAR
    @app.route(f'/{endpoint}/<int:id>', methods=['GET', 'PUT', 'DELETE'])
    def handle_item_by_id(id):
        item = model.query.get_or_404(id)

        if request.method == 'GET':
            return jsonify(item.to_dict()), 200

        elif request.method == 'PUT':
            data = request.get_json()
            
            try:
                # Actualización de atributos
                for key, value in data.items():
                    if hasattr(item, key) and key != 'id':
                        setattr(item, key, value)
                
                db.session.commit()
                return jsonify({'mensaje': f'{model.__name__} actualizado', endpoint: item.to_dict()}), 200
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error al actualizar {model.__name__}: {e}")
                return jsonify({'error': f'Error interno al actualizar: {str(e)}'}), 500

        elif request.method == 'DELETE':
            try:
                db.session.delete(item)
                db.session.commit()
                return jsonify({'mensaje': f'{model.__name__} eliminado correctamente'}), 200
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error al eliminar {model.__name__}: {e}")
                return jsonify({'error': f'Error interno al eliminar: {str(e)}'}), 500

# --- INICIALIZACIÓN DE RUTAS ---

create_crud_routes(app, Usuario, 'usuarios', ['nombre', 'email', 'rol'])
create_crud_routes(app, Pedido, 'pedidos', ['nombre_cliente', 'direccion_entrega'])
create_crud_routes(app, Ruta, 'rutas', ['nombre_ruta', 'zona_asignada'])

# --- RUTA DE INICIO ---

@app.route('/')
def index():
    return jsonify({"mensaje": "API de Logística (Usuarios, Pedidos, Rutas) funcionando correctamente 🚚"})

# --- INICIALIZACIÓN DE LA APLICACIÓN ---

# Crear tablas si no existen (se ejecuta al iniciar la app)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Obtiene el puerto asignado por Render (o usa 5000 por defecto para desarrollo local)
    port = int(os.environ.get('PORT', 5000)) 
    # Asegura que la aplicación escuche en todas las interfaces ('0.0.0.0')
    app.run(host='0.0.0.0', port=port)