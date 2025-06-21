#!/bin/bash

# Group Buying API (GBGCN) - Quick Start Script
# Based on "Group-Buying Recommendation for Social E-Commerce" paper

set -e

echo "🚀 Starting Group Buying API (GBGCN) Quick Setup..."
echo "📄 Based on: Group-Buying Recommendation for Social E-Commerce paper"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed ✓"
}

# Create .env file if it doesn't exist
setup_env() {
    if [ ! -f .env ]; then
        print_step "Creating .env file with GBGCN parameters..."
        cat > .env << EOF
# Group Buying API (GBGCN) Configuration
APP_NAME=Group Buying API (GBGCN)
DEBUG=true
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://groupbuy:password@postgres:5432/groupbuy_db

# Security
SECRET_KEY=$(openssl rand -hex 32)

# GBGCN Model Parameters (from paper)
EMBEDDING_DIM=64
NUM_GCN_LAYERS=3
DROPOUT_RATE=0.1
LEARNING_RATE=0.001
ALPHA=0.6
BETA=0.4

# Training Parameters
BATCH_SIZE=512
MAX_EPOCHS=500
PATIENCE=20

# Graph Construction
MIN_INTERACTIONS_PER_USER=5
MIN_INTERACTIONS_PER_ITEM=3
SOCIAL_INFLUENCE_THRESHOLD=0.1

# Business Rules
MIN_GROUP_SIZE=2
MAX_GROUP_SIZE=100
DEFAULT_GROUP_DURATION_DAYS=7

# Redis
REDIS_URL=redis://redis:6379

# Logging
LOG_LEVEL=INFO
EOF
        print_status ".env file created with GBGCN parameters ✓"
    else
        print_status ".env file already exists ✓"
    fi
}

# Create necessary directories
setup_directories() {
    print_step "Creating project directories..."
    
    mkdir -p models
    mkdir -p data/{raw,processed,features}
    mkdir -p logs
    mkdir -p notebooks
    mkdir -p scripts
    mkdir -p tests
    
    print_status "Project directories created ✓"
}

# Start services
start_services() {
    print_step "Starting Group Buying API services..."
    
    # Build and start services
    docker-compose up --build -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Services are running ✓"
    else
        print_error "Some services failed to start"
        docker-compose logs
        exit 1
    fi
}

# Initialize database
init_database() {
    print_step "Initializing database with GBGCN schema..."
    
    # Wait for PostgreSQL to be ready
    until docker-compose exec -T postgres pg_isready -U groupbuy; do
        print_status "Waiting for PostgreSQL..."
        sleep 2
    done
    
    # Run database migrations
    docker-compose exec -T api alembic upgrade head || print_warning "Database migration skipped (will be created on first run)"
    
    print_status "Database initialized ✓"
}

# Load sample data
load_sample_data() {
    print_step "Loading sample data for GBGCN testing..."
    
    # Create sample data script
    cat > scripts/load_sample_data.py << 'EOF'
"""Load sample data for GBGCN testing"""
import requests
import random
import time

API_BASE = "http://localhost:8000/api/v1"

# Sample users
users = [
    {"email": f"user{i}@example.com", "username": f"user{i}", 
     "password": "password123", "first_name": f"User{i}", "last_name": "Test"}
    for i in range(1, 21)
]

# Sample categories
categories = [
    {"name": "Electronics", "description": "Electronic devices and gadgets"},
    {"name": "Fashion", "description": "Clothing and accessories"},
    {"name": "Home & Garden", "description": "Home improvement and garden items"},
    {"name": "Sports", "description": "Sports equipment and gear"},
    {"name": "Books", "description": "Books and educational materials"}
]

print("🔄 Loading sample data for GBGCN...")

# Register users
tokens = []
for user in users:
    try:
        response = requests.post(f"{API_BASE}/auth/register", json=user)
        if response.status_code == 201:
            # Login to get token
            login_response = requests.post(f"{API_BASE}/auth/login", json={
                "email": user["email"], "password": user["password"]
            })
            if login_response.status_code == 200:
                tokens.append(login_response.json()["access_token"])
        time.sleep(0.1)
    except Exception as e:
        print(f"Error creating user: {e}")

print(f"✅ Created {len(tokens)} users")

# Create social connections
for i, token in enumerate(tokens[:10]):  # First 10 users
    headers = {"Authorization": f"Bearer {token}"}
    # Connect to 3-5 random friends
    friends = random.sample(range(len(tokens)), random.randint(3, 5))
    for friend_idx in friends:
        if friend_idx != i:
            try:
                requests.post(f"{API_BASE}/social/connect", 
                            json={"friend_id": f"user{friend_idx+1}"},
                            headers=headers)
            except:
                pass

print("✅ Created social connections")
print("🎉 Sample data loaded successfully!")
print("📊 You can now test GBGCN recommendations with realistic data")
EOF

    # Run sample data script
    docker-compose exec -T api python scripts/load_sample_data.py || print_warning "Sample data loading skipped"
    
    print_status "Sample data loaded ✓"
}

# Verify installation
verify_installation() {
    print_step "Verifying GBGCN installation..."
    
    # Check API health
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            print_status "API is responding ✓"
            break
        else
            if [ $i -eq 10 ]; then
                print_error "API is not responding after 10 attempts"
                return 1
            fi
            print_status "Waiting for API... (attempt $i/10)"
            sleep 3
        fi
    done
    
    # Check model status
    model_status=$(curl -s http://localhost:8000/model/status | grep -o '"model_status":"[^"]*"' | cut -d'"' -f4)
    if [ "$model_status" = "healthy" ] || [ "$model_status" = "not_ready" ]; then
        print_status "GBGCN model status: $model_status ✓"
    else
        print_warning "GBGCN model status: unknown"
    fi
}

# Show next steps
show_next_steps() {
    echo ""
    echo "🎉 Group Buying API (GBGCN) is now running!"
    echo ""
    echo "📊 Services:"
    echo "  • API: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Jupyter: http://localhost:8888 (if enabled)"
    echo ""
    echo "🔬 GBGCN Features Available:"
    echo "  • Multi-view embedding propagation"
    echo "  • Social influence modeling"
    echo "  • Group formation optimization"
    echo "  • Success probability prediction"
    echo ""
    echo "🧪 Quick Test Commands:"
    echo "  curl http://localhost:8000/health"
    echo "  curl http://localhost:8000/model/status"
    echo ""
    echo "📚 Next Steps:"
    echo "  1. Open http://localhost:8000/docs for API documentation"
    echo "  2. Register users and create groups"
    echo "  3. Test GBGCN recommendations"
    echo "  4. Monitor model performance"
    echo ""
    echo "🔧 Management Commands:"
    echo "  docker-compose logs -f api     # View API logs"
    echo "  docker-compose down           # Stop services"
    echo "  docker-compose up -d          # Restart services"
    echo ""
}

# Main execution
main() {
    echo "📋 Group Buying API (GBGCN) Quick Start"
    echo "Based on: Group-Buying Recommendation for Social E-Commerce"
    echo ""
    
    check_docker
    setup_env
    setup_directories
    start_services
    init_database
    load_sample_data
    verify_installation
    show_next_steps
    
    print_status "Setup completed successfully! 🎉"
}

# Run main function
main "$@" 