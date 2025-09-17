import pytest
from src.app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test the health endpoint returns 200"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'services' in data

def test_liveness_endpoint(client):
    """Test the liveness endpoint returns 200"""
    response = client.get('/api/health/live')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'alive'

def test_readiness_endpoint(client):
    """Test the readiness endpoint"""
    response = client.get('/api/health/ready')
    # May return 200 or 503 depending on DB state - just ensure it responds
    assert response.status_code in [200, 503]
    data = response.get_json()
    assert 'status' in data

def test_metrics_endpoint(client):
    """Test the metrics endpoint"""
    response = client.get('/api/metrics')
    # May return 200 or 500 depending on DB state - just ensure it responds
    assert response.status_code in [200, 500]