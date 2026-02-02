#!/bin/bash
# deploy.sh - Deploy Shark Command Center

echo "🦈 Deploying Shark Command Center..."

# 1. Clone dweepbot if not exists
if [ ! -d "dweepbot" ]; then
    echo "📥 Cloning dweepbot repository..."
    git clone https://github.com/dweepbot/dweepbot.git
    cd dweepbot
    pip install -e ".[all]"
    cd ..
fi

# 2. Install backend dependencies
echo "📦 Installing backend dependencies..."
pip install fastapi uvicorn websockets python-multipart

# 3. Create workspace directory
mkdir -p workspace

# 4. Set up environment variables
if [ ! -f ".env" ]; then
    echo "🔑 Setting up environment..."
    cat > .env << EOF
DEEPSEEK_API_KEY=your_api_key_here
DWEEPBOT_WORKSPACE_PATH=./workspace
DWEEPBOT_ENABLE_WEB_SEARCH=true
DWEEPBOT_ENABLE_CODE_EXECUTION=true
DWEEPBOT_MAX_COST_USD=10.0
EOF
    echo "⚠️  Please update .env with your DeepSeek API key"
fi

# 5. Start backend server
echo "🚀 Starting backend server..."
python api_server.py &

# 6. Start frontend (assuming React app)
echo "🎨 Starting frontend..."
# If using Create React App:
# npm start
# If using Vite:
# npm run dev

echo "✅ Deployment complete!"
echo "📡 Backend: http://localhost:8000"
echo "🎨 Frontend: http://localhost:3000"
echo "📚 API Docs: http://localhost:8000/docs"
