#!/bin/bash

# ============================================================================
# PDF Document Extraction and Semantic Chunking - Run Script
# ============================================================================
# This script runs the document processing pipeline with configurable parameters
# ============================================================================

# Configuration Parameters
# ============================================================================

# Input folder containing the hierarchical structure (company/year/documents.pdf)
INPUT_FOLDER="reports/"

# Output JSON file path
OUTPUT_FILE="output.json"

# Semantic Chunking Parameters
# ============================================================================

# Enable/disable semantic chunking (set to "--no-chunking" to disable, or "" to enable)
NO_CHUNKING=""

# Similarity threshold for semantic chunking (0.0 to 1.0)
# Lower values create more chunks (more aggressive splitting)
# Higher values create fewer chunks (keep more text together)
# Recommended range: 0.4 - 0.7
SIMILARITY_THRESHOLD=0.5

# Minimum number of sentences per chunk
# Prevents creating very small chunks
MIN_CHUNK_SIZE=5

# Maximum number of sentences per chunk
# Prevents creating very large chunks
MAX_CHUNK_SIZE=20

# Output Formatting
# ============================================================================

# Pretty print JSON output (set to "--pretty" for formatted output, or "" for compact)
PRETTY_PRINT="--pretty"

# AI Extraction Parameters
# ============================================================================

# Skip titles and subtitles extraction (set to "--skip-titles" to skip, or "" to include)
SKIP_TITLES="--skip-titles"

# Enable AI-based sustainability data extraction (set to "--ai-extraction" to enable, or "" to disable)
# Requires Ollama to be running locally
AI_EXTRACTION="--ai-extraction"

# Ollama model to use for AI extraction (default: llama3)
# OLLAMA_MODEL="llama3.2:3b"

# AI Extraction Model Type (set to "ollama" or "openai")
# MODEL_TYPE="ollama"
MODEL_TYPE="openai"

# OpenAI Model (reusing OLLAMA_MODEL variable name for simplicity in script, though it's confusing)
# If using OpenAI, set this to the OpenAI model name (e.g. gpt-4o, gpt-3.5-turbo)
OLLAMA_MODEL="gpt-3.5-turbo"

# OpenAI API Key (leave empty to use .env file or environment variable)
OPENAI_API_KEY=""

# Load .env file if available and key not set check
if [ -z "$OPENAI_API_KEY" ] && [ -f ".env" ]; then
    # Export all variables from .env
    export $(grep -v '^#' .env | xargs)
    # If OPENAI_API_KEY was in .env, it's now exported.
fi

# ============================================================================
# Script Execution
# ============================================================================

echo "============================================================================"
echo "PDF Document Extraction and Semantic Chunking"
echo "============================================================================"
echo ""
echo "Configuration:"
echo "  Input Folder:          $INPUT_FOLDER"
echo "  Output File:           $OUTPUT_FILE"
echo "  Semantic Chunking:     $([ -z "$NO_CHUNKING" ] && echo "Enabled" || echo "Disabled")"
echo "  Similarity Threshold:  $SIMILARITY_THRESHOLD"
echo "  Min Chunk Size:        $MIN_CHUNK_SIZE sentences"
echo "  Max Chunk Size:        $MAX_CHUNK_SIZE sentences"
echo "  Pretty Print:          $([ -n "$PRETTY_PRINT" ] && echo "Yes" || echo "No")"
echo "  Skip Titles:           $([ -n "$SKIP_TITLES" ] && echo "Yes" || echo "No")"
echo "  AI Extraction:         $([ -n "$AI_EXTRACTION" ] && echo "Enabled ($MODEL_TYPE: $OLLAMA_MODEL)" || echo "Disabled")"
echo ""
echo "============================================================================"
echo ""

# Check if input folder exists
if [ ! -d "$INPUT_FOLDER" ]; then
    echo "❌ Error: Input folder '$INPUT_FOLDER' does not exist!"
    echo "Please create the folder or update INPUT_FOLDER in this script."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if required Python packages are installed
echo "Checking dependencies..."
python3 -c "import fitz, sentence_transformers, numpy, langchain, langchain_ollama" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Some dependencies are missing."
    echo "Installing dependencies from requirements.txt..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install dependencies"
        exit 1
    fi
fi

echo "✓ Dependencies OK"
echo ""

# Build the command
CMD="python3 main.py \"$INPUT_FOLDER\" \
    --output \"$OUTPUT_FILE\" \
    --similarity-threshold $SIMILARITY_THRESHOLD \
    --min-chunk-size $MIN_CHUNK_SIZE \
    --max-chunk-size $MAX_CHUNK_SIZE"

# Add optional flags
[ -n "$NO_CHUNKING" ] && CMD="$CMD $NO_CHUNKING"
[ -n "$PRETTY_PRINT" ] && CMD="$CMD $PRETTY_PRINT"
[ -n "$SKIP_TITLES" ] && CMD="$CMD $SKIP_TITLES"
[ -n "$AI_EXTRACTION" ] && CMD="$CMD $AI_EXTRACTION --model-type $MODEL_TYPE --ollama-model $OLLAMA_MODEL"
[ -n "$OPENAI_API_KEY" ] && CMD="$CMD --openai-api-key $OPENAI_API_KEY"

# Display the command being executed
echo "Executing command:"
echo "$CMD"
echo ""
echo "============================================================================"
echo ""

# Execute the command
eval $CMD

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================================"
    echo "✓ Processing completed successfully!"
    echo "✓ Output saved to: $OUTPUT_FILE"
    echo "============================================================================"
else
    echo ""
    echo "============================================================================"
    echo "❌ Processing failed!"
    echo "============================================================================"
    exit 1
fi
