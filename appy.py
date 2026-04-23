from flask import Flask, render_template
from flask_socketio import SocketIO, send

# crear la aplicación Flask y configurar socketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app)

#ruta principal
@app.route('/')

#funcion para mostrar la interfaz del chat
def index():
    return render_template('chat.html') #utilizar archivo externo (html) para mostrar la interfaz del chat

#funcion para manejar los mensajes enviados por los clientes
@socketio.on('message')
def handle_message(msg):
    print('Mensaje recibido: ' + msg) #imprimir el mensaje recibido en la consola del servidor
    send(msg, broadcast=True) #enviar el mensaje a todos los clientes conectados

#iniciar el servidor de socketIO
if __name__ == '__main__':
    socketio.run(app, debug=True)