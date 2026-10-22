import json
from pathlib import Path
import sys
import types
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.src import main, models
from app.src.metadata import position_at_frame


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    models.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)
    def db():
        with session() as value:
            yield value
    main.app.dependency_overrides[main.get_db] = db
    monkeypatch.setattr(main, 'UPLOAD_DIR', tmp_path / 'uploads')
    with TestClient(main.app) as value:
        yield value
    main.app.dependency_overrides.clear()
    engine.dispose()


def upload(client, metadata=None, model='custom', video=b'video'):
    if metadata is None:
        metadata = json.dumps({'dynamicMetadata': [{'latitude': 44, 'longitude': 20}]}).encode()
    return client.post('/upload-video/', data={'model': model}, files={
        'video_file': ('../../outside.mp4', video, 'video/mp4'),
        'metadata': ('../../outside.json', metadata, 'application/json')})


def test_pagination_and_serialization(client):
    for i in range(3):
        response = client.post('/potholes/', json={'class_name': str(i), 'latitude': 44, 'longitude': 20, 'confidence': .8})
        assert response.status_code == 200
    response = client.get('/potholes/?skip=1&limit=1')
    assert [row['class_name'] for row in response.json()] == ['1']
    assert 'detected_at' in response.json()[0]


@pytest.mark.parametrize('query', ['skip=-1', 'limit=0', 'limit=1001'])
def test_invalid_pagination(client, query):
    assert client.get('/potholes/?' + query).status_code == 422


def test_unknown_model(client):
    assert upload(client, model='unknown').status_code == 422
    assert not main.UPLOAD_DIR.exists()


@pytest.mark.parametrize('metadata', [b'not json', b'{"dynamicMetadata": []}', b'{"dynamicMetadata": [{"latitude": 91, "longitude": 20}]}'])
def test_invalid_metadata_cleanup(client, metadata):
    assert upload(client, metadata=metadata).status_code == 422
    assert list(main.UPLOAD_DIR.iterdir()) == []


def test_size_limit_cleanup(client, monkeypatch):
    monkeypatch.setattr(main, 'MAX_VIDEO_BYTES', 2)
    assert upload(client).status_code == 413
    assert list(main.UPLOAD_DIR.iterdir()) == []


def test_empty_video_cleanup(client):
    assert upload(client, video=b'').status_code == 400
    assert list(main.UPLOAD_DIR.iterdir()) == []


def test_accepted_job_uses_generated_filenames(client, monkeypatch):
    recorded = []
    monkeypatch.setattr(main, 'process_video_analysis', lambda *args: recorded.append(args))
    response = upload(client)
    assert response.status_code == 202
    job = response.json()['job_id']
    assert recorded[0][0] == main.UPLOAD_DIR / job / 'video.mp4'
    assert recorded[0][3] == main.UPLOAD_DIR / job / 'metadata.json'


def test_background_failure_closes_session_and_removes_inputs(tmp_path, monkeypatch):
    directory = tmp_path / 'job'
    directory.mkdir()
    video = directory / 'video.mp4'
    video.write_bytes(b'video')
    closed = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): closed.append(True)
    class Processor:
        def __init__(self, **kwargs): raise RuntimeError('model unavailable')
    monkeypatch.setattr(main, 'SessionLocal', Session)
    monkeypatch.setitem(sys.modules, 'app.src.video_processor', types.SimpleNamespace(VideoProcessor=Processor))
    main.process_video_analysis(video, 'job', 'custom', directory / 'metadata.json')
    assert closed == [True]
    assert not directory.exists()


def test_metadata_sampling_handles_short_gps_stream():
    positions = [(44, 20), (45, 21)]
    assert position_at_frame(positions, 1, 60) == positions[0]
    assert position_at_frame(positions, 2, 60) == positions[1]
    assert position_at_frame(positions, 1000, 60) == positions[-1]
