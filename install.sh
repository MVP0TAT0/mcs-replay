#!/bin/bash

set -e

echo "Creating virtual environment..."

python3 -m venv venv

echo "Activating virtual environment..."

source venv/bin/activate

echo "Upgrading pip..."

pip install --upgrade pip

echo "Installing requirements..."

pip install -r requirements.txt

echo ""
echo "Installation complete."
echo ""
echo "Activate the environment with:"
echo "source venv/bin/activate"