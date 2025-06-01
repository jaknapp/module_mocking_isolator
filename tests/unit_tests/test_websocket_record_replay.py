import pytest
import websockets
from mock_isolator.recording_mock import RecordingMock, BasicRecordingMocker
from mock_isolator.replaying_mock import ReplayingMock


class WebSocketClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.connection = None

    async def connect(self):
        self.connection = await websockets.connect(self.uri)
        return self.connection

    async def send(self, message: str):
        await self.connection.send(message)

    async def recv(self) -> str:
        return await self.connection.recv()

    async def close(self):
        await self.connection.close()


@pytest.mark.asyncio
async def test_websocket_recording(tmp_path):
    received_messages = []

    async def echo_server(websocket):
        async for message in websocket:
            received_messages.append(message)
            await websocket.send(f"echo: {message}")

    server = await websockets.serve(echo_server, "localhost", 8765)

    mocker = BasicRecordingMocker()
    client = WebSocketClient("ws://localhost:8765")
    wrapped_client = RecordingMock(client, mocker)

    await wrapped_client.connect()
    await wrapped_client.send("hello")
    response = await wrapped_client.recv()
    await wrapped_client.close()

    assert response == "echo: hello"
    assert received_messages == ["hello"]

    server.close()
    await server.wait_closed()


@pytest.mark.asyncio
async def test_websocket_replay():
    mock = ReplayingMock(
        recorded_attribute_accesses={
            "connect": [None],
            "send": [None],
            "recv": ["echo: hello"],
            "close": [None],
        },
        recorded_calls=[],
        target_type=WebSocketClient
    )

    await mock.connect()
    await mock.send("hello")
    response = await mock.recv()
    await mock.close()

    assert response == "echo: hello"
