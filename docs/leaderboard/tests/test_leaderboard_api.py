#!/usr/bin/env python3
"""
Tests for the Multi-Language Translation Leaderboard API
Tests the core leaderboard functionality: submit models, get rankings, get test data
"""

import requests
import json
import os
import pytest

# API URL configuration with environment detection
def get_api_base_url():
    """Get the base API URL with environment detection"""
    # 1. Check environment variable first (for CI/CD flexibility)
    if os.getenv('TEST_API_BASE_URL'):
        return os.getenv('TEST_API_BASE_URL')
    
    # 2. Check if running inside Docker container
    if os.path.exists('/.dockerenv'):
        return "http://localhost:5000"
    
    # 3. Try to detect if we're in CI environment
    if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
        return "http://localhost:5000"  # CI usually runs services on internal ports
    
    # 4. Default to external port for local development
    return "http://localhost:5001"

def check_api_available():
    """Check if the API is available for testing"""
    try:
        api_url = get_api_base_url()
        response = requests.get(f"{api_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

# Skip all tests if API is not available
pytestmark = pytest.mark.skipif(
    not check_api_available(),
    reason=f"API not available at {get_api_base_url()}"
)

API_BASE_URL = get_api_base_url()

def test_get_source_sentences():
    """Test /public/get_source_sentences - Get test sentences for translation"""
    print("\n🧪 Testing /public/get_source_sentences")
    
    response = requests.get(
        f"{API_BASE_URL}/public/get_source_sentences",
        params={"count": 3, "start_idx": 0}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data.get('success') is True
    assert 'sentence_ids' in data
    assert 'source_sentences' in data
    assert len(data['sentence_ids']) == 3
    assert len(data['source_sentences']) == 3
    
    print(f"✅ Got {len(data['sentence_ids'])} test sentences")
    return data['sentence_ids'], data['source_sentences']

def test_submit_model_basic():
    """Test /public/submit_model - Submit translation results to leaderboard"""
    print("\n🧪 Testing /public/submit_model")
    
    # Get test sentences first
    sentence_ids, _ = test_get_source_sentences()
    
    # Create test translations
    test_translations = [
        "Esta es una traducción de prueba.",
        "Esta es otra traducción de prueba.", 
        "Esta es la tercera traducción de prueba."
    ][:len(sentence_ids)]
    
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-model-basic",
        "modelResults": test_translations,
        "sentence_ids": sentence_ids
    }
    
    response = requests.post(
        f"{API_BASE_URL}/public/submit_model",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data.get('success') is True
    assert 'score' in data  # API returns 'score' not 'bleu_score'
    assert isinstance(data['score'], (int, float))
    
    print(f"✅ Model submitted successfully, score: {data['score']}")

def test_get_leaderboard():
    """Test /public/get_leaderboard - Get current leaderboard rankings"""
    print("\n🧪 Testing /public/get_leaderboard")
    
    response = requests.get(f"{API_BASE_URL}/public/get_leaderboard")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data.get('success') is True
    assert 'leaderboard' in data
    assert isinstance(data['leaderboard'], list)
    
    # Should have multiple leaderboard entries
    assert len(data['leaderboard']) > 0
    
    # Check structure of leaderboard entries
    if data['leaderboard']:
        entry = data['leaderboard'][0]
        required_fields = ['dataset_name', 'evaluation_metric', 'model_name', 'score']  # API uses 'evaluation_metric'
        for field in required_fields:
            assert field in entry, f"Missing field: {field}"
    
    print(f"✅ Got leaderboard with {len(data['leaderboard'])} entries")

def test_submit_model_validation():
    """Test /public/submit_model validation scenarios"""
    print("\n🧪 Testing /public/submit_model validation")
    
    # Test missing sentence_ids
    payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-validation",
        "modelResults": ["Test translation"]
        # Missing sentence_ids
    }
    
    response = requests.post(
        f"{API_BASE_URL}/public/submit_model",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Should return error for missing sentence_ids
    assert response.status_code == 400
    data = response.json()
    assert data.get('success') is False
    assert 'error' in data
    
    print("✅ Validation correctly rejected missing sentence_ids")

def test_translation_quality_scoring():
    """Test that the API produces reasonable BLEU scores for different quality translations"""
    print("\n🧪 Testing translation quality scoring")
    
    # Get test sentences
    sentence_ids, source_sentences = test_get_source_sentences()
    
    # High-quality translations (close to reference)
    high_quality = [
        "«Actualmente, tenemos ratones de cuatro meses de edad que antes solían ser diabéticos y que ya no lo son», agregó.",
        "La investigación todavía se ubica en su etapa inicial, según el Dr. Ehud Ur, profesor de medicina de la Universidad de Dalhousie.",
        "Como algunos otros expertos, es escéptico sobre si la diabetes puede curarse, en lugar de simplemente controlarse."
    ][:len(sentence_ids)]
    
    # Low-quality translations (completely wrong)
    low_quality = [
        "The cat sat on the mat.",
        "Hello world, this is wrong.",
        "Random text that makes no sense."
    ][:len(sentence_ids)]
    
    # Test high-quality translations
    high_payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-high-quality",
        "modelResults": high_quality,
        "sentence_ids": sentence_ids
    }
    
    high_response = requests.post(f"{API_BASE_URL}/public/submit_model", json=high_payload)
    assert high_response.status_code == 200
    high_score = high_response.json()['score']  # API returns 'score' not 'bleu_score'
    
    # Test low-quality translations  
    low_payload = {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "test-low-quality",
        "modelResults": low_quality,
        "sentence_ids": sentence_ids
    }
    
    low_response = requests.post(f"{API_BASE_URL}/public/submit_model", json=low_payload)
    assert low_response.status_code == 200
    low_score = low_response.json()['score']  # API returns 'score' not 'bleu_score'
    
    # High-quality should score better than low-quality
    assert high_score > low_score, f"High quality ({high_score}) should score better than low quality ({low_score})"
    
    print(f"✅ Quality scoring works: High={high_score:.3f}, Low={low_score:.3f}") 