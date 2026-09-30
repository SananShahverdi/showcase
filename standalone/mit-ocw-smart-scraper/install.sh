#!/bin/bash

# MIT OCW Smart Scraper Installation Script
# Automates setup process for Linux/macOS

set -e

echo "=================================="
echo "MIT OCW Smart Scraper Setup"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo -e "${RED}Python 3.8+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}✓ Virtual environment created${NC}"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt
echo ""
echo "Installing project dependencies..."
pip install -r requirements.txt

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Ask about optional features
echo ""
echo -e "${YELLOW}Optional Features:${NC}"
echo ""

# Selenium
read -p "Install Selenium for better course discovery? (y/n): " install_selenium
if [[ $install_selenium == "y" ]]; then
    echo "Installing Selenium..."
    pip install selenium webdriver-manager
    echo -e "${GREEN}✓ Selenium installed${NC}"
fi

# Whisper
echo ""
read -p "Install Whisper for audio transcription? (y/n): " install_whisper
if [[ $install_whisper == "y" ]]; then
    # Check for FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${YELLOW}Warning: FFmpeg not found${NC}"
        echo "Whisper requires FFmpeg for audio processing"
        echo ""
        echo "Install FFmpeg:"
        echo "  Linux: sudo apt-get install ffmpeg"
        echo "  macOS: brew install ffmpeg"
        echo ""
        read -p "Continue anyway? (y/n): " continue_whisper
        if [[ $continue_whisper != "y" ]]; then
            echo "Skipping Whisper installation"
            install_whisper="n"
        fi
    fi
    
    if [[ $install_whisper == "y" ]]; then
        echo "Installing Whisper..."
        pip install openai-whisper
        
        # Ask about PyTorch
        echo ""
        echo "Whisper requires PyTorch"
        read -p "Do you have an NVIDIA GPU? (y/n): " has_gpu
        
        if [[ $has_gpu == "y" ]]; then
            echo "Installing PyTorch with CUDA support..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        else
            echo "Installing PyTorch (CPU only)..."
            pip install torch torchvision torchaudio
        fi
        
        echo -e "${GREEN}✓ Whisper installed${NC}"
    fi
fi

# Additional PDF tools
echo ""
read -p "Install additional PDF processing tools? (y/n): " install_pdf_tools
if [[ $install_pdf_tools == "y" ]]; then
    echo "Installing PDF tools..."
    pip install PyMuPDF Pillow
    echo -e "${GREEN}✓ PDF tools installed${NC}"
fi

# Testing tools
echo ""
read -p "Install testing tools (for development)? (y/n): " install_test_tools
if [[ $install_test_tools == "y" ]]; then
    echo "Installing testing tools..."
    pip install pytest pytest-cov pytest-mock black flake8
    echo -e "${GREEN}✓ Testing tools installed${NC}"
fi

# Create config file
echo ""
echo "Creating default config file..."
if [ ! -f "config.yaml" ]; then
    if [ -f "config.example.yaml" ]; then
        cp config.example.yaml config.yaml
        echo -e "${GREEN}✓ Copied config.example.yaml to config.yaml${NC}"
    else
        echo "output:" > config.yaml
        echo "  base_directory: \"MIT_OCW_Courses\"" >> config.yaml
        echo -e "${YELLOW}config.example.yaml not found; created minimal config${NC}"
    fi
else
    echo -e "${YELLOW}Config file already exists, skipping${NC}"
fi

# Create output directory
echo ""
echo "Creating output directory..."
mkdir -p MIT_OCW_Courses
echo -e "${GREEN}✓ Output directory created${NC}"

# Final instructions
echo ""
echo "=================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run diagnostics: python smart_scraper.py --self-test"
echo "     (review MIT_OCW_Courses/scraper.log for [FAIL]/[WARN] entries)"
echo "  3. Start scraping: python smart_scraper.py \"https://ocw.mit.edu/search/?d=Physics\""
echo ""
echo "Configuration file: config.yaml"
echo "Output directory: MIT_OCW_Courses/"
echo ""
echo "For help: python smart_scraper.py --help"
echo ""

# Offer to run test
if [[ $install_test_tools == "y" ]]; then
    echo ""
    read -p "Run tests to verify installation? (y/n): " run_tests
    if [[ $run_tests == "y" ]]; then
        echo ""
        echo "Running tests..."
        pytest test_scraper.py -v || echo -e "${YELLOW}Some tests failed, but installation is complete${NC}"
    fi
fi

echo ""
echo -e "${GREEN}Happy scraping! 🎓${NC}"
