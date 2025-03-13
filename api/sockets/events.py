from .server import sio  # Импортируем sio из server.py

def register_socket_events():
    @sio.event
    async def connect(sid, environ):
        print(f"Клиент {sid} подключился")
        await sio.emit("welcome", {"message": "Добро пожаловать!"}, to=sid)

    @sio.event
    async def disconnect(sid):
        print(f"Клиент {sid} отключился")