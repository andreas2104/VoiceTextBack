import os
from flask import Blueprint, request, jsonify


OLLAMA_URL  = os.getenv("OLLAMA_URL", "http://localhost:11434")



