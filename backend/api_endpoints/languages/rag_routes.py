"""
Simple Flask API for Anote RAG Chatbot
Can be integrated with Autonomous-Intelligence UI
"""

from flask import Blueprint, request, jsonify
import os
import sys
import json
from datetime import datetime

from rag_service.rag_agent import create_anote_agent

rag_blueprint = Blueprint('anote_rag', __name__)

print("Initializing Anote RAG Agent...")
try:
    agent = create_anote_agent()
    print("Agent initialized successfully")
except Exception as e:
    print(f"Error initializing agent: {e}")
    sys.exit(1)


@rag_blueprint.route("/api/chat/anote", methods=["POST"])
def chat_anote():
    try:
        if agent is None:
            return jsonify({"error": "RAG agent not initialized"}), 500

        messages_json = request.form.get("messages")
        
        if not messages_json:
            return jsonify({"error": "Missing messages"}), 400

        messages = json.loads(messages_json)
        question = messages[-1]["content"]
        
        result = agent.query(question)
        
        return jsonify({"response": result['answer']})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@rag_blueprint.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Quick test to verify agent works
        agent_status = 'operational' if agent.qa_chain is not None else 'degraded'
        
        return jsonify({
            'status': 'healthy',
            'agent_status': agent_status,
            'service': 'Anote RAG Chatbot',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@rag_blueprint.route('/agent/info', methods=['GET'])
def get_agent_info():
    """Get information about the agent."""
    info = agent.get_agent_info()
    return jsonify(info)


@rag_blueprint.route('/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint.
    
    Request body:
    {
        "question": "What is Anote?",
        "include_sources": true  // optional, default true
    }
    
    Response:
    {
        "success": true,
        "question": "What is Anote?",
        "answer": "...",
        "sources": [...],
        "num_sources": 3,
        "timestamp": "2025-01-15T10:30:00"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: question'
            }), 400
        
        question = data['question'].strip()
        include_sources = data.get('include_sources', True)
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Question cannot be empty'
            }), 400
        
        # Query
        result = agent.query(question)
        
        # Optional: remove sources
        if not include_sources:
            result.pop('sources', None)
        
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@rag_blueprint.route('/chat/batch', methods=['POST'])
def batch_chat():
    """
    Batch processing endpoint.
    
    Request body:
    {
        "questions": ["What is Anote?", "What are Anote's products?"]
    }
    
    Response:
    {
        "success": true,
        "results": [...],
        "total_questions": 2,
        "timestamp": "2025-01-15T10:30:00"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'questions' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: questions'
            }), 400
        
        questions = data['questions']
        
        if not isinstance(questions, list):
            return jsonify({
                'success': False,
                'error': 'questions must be a list'
            }), 400
        
        if len(questions) == 0:
            return jsonify({
                'success': False,
                'error': 'questions list cannot be empty'
            }), 400
        
        # Process batch
        results = agent.batch_query(questions)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_questions': len(questions),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@rag_blueprint.route('/predictions/initial', methods=['GET'])
def get_initial_predictions():
    """
    Get the initial predictions for submission to Anote.
    Reads from initial_predictions.json if it exists.
    """
    try:
        predictions_file = 'initial_predictions.json'
        
        if not os.path.exists(predictions_file):
            # Generate new predictions
            test_questions = [
                "What is Anote?",
                "What are Anote's main products?",
                "How does Anote use fine-tuning?",
                "What is the Anote platform used for?",
                "How does Anote help with LLM evaluation?"
            ]
            
            results = agent.batch_query(test_questions)
            
            # Save for future use
            with open(predictions_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'predictions': results,
                'note': 'Generated new predictions',
                'timestamp': datetime.now().isoformat()
            })
        
        # Load existing predictions
        with open(predictions_file, 'r', encoding='utf-8') as f:
            predictions = json.load(f)
        
        return jsonify({
            'success': True,
            'predictions': predictions,
            'note': 'Loaded existing predictions',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Error handlers
@rag_blueprint.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@rag_blueprint.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500
