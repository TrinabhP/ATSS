#!/usr/bin/env bash
# Render build script — installs Python deps + builds React frontend
set -o errexit

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt
pip install fastapi uvicorn python-multipart fpdf2 certifi supabase pyjwt requests groq

echo "=== Building React frontend ==="
cd labos-mockup
npm install
npm run build
cd ..

echo "=== Build complete ==="
