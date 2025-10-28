#!/bin/bash

# Production deployment script for RAG-bidding application
# This script handles the complete deployment process from the docker folder

set -e  # Exit on any error

# Configuration
PROJECT_NAME="rag-bidding"
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"localhost:5000"}
VERSION=${VERSION:-"latest"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$DOCKER_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
    fi
    
    # Check for .env file in docker/config or project root
    if [ ! -f "$PROJECT_ROOT/.env" ] && [ ! -f "$DOCKER_DIR/config/.env" ]; then
        warn ".env file not found. Creating from template..."
        if [ -f "$DOCKER_DIR/config/.env.example" ]; then
            cp "$DOCKER_DIR/config/.env.example" "$PROJECT_ROOT/.env"
        elif [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        fi
        warn "Please edit .env file with your configuration before proceeding"
        exit 1
    fi
    
    log "Prerequisites check passed"
}

# Build application
build_app() {
    log "Building application..."
    
    cd "$PROJECT_ROOT"
    
    # Determine which Dockerfile to use
    if [ "$USE_GPU" == "true" ]; then
        DOCKERFILE="docker/Dockerfile.cuda"
        COMPOSE_FILE="docker/compose/docker-compose.cuda.yml"
        log "Building with GPU support"
    else
        DOCKERFILE="docker/Dockerfile"
        COMPOSE_FILE="docker/compose/docker-compose.yml"
        log "Building with CPU support"
    fi
    
    # Build the image
    docker build -f $DOCKERFILE -t ${PROJECT_NAME}:${VERSION} .
    
    # Tag for registry if specified
    if [ "$DOCKER_REGISTRY" != "localhost:5000" ]; then
        docker tag ${PROJECT_NAME}:${VERSION} ${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION}
    fi
    
    log "Build completed successfully"
}

# Deploy application
deploy_app() {
    log "Deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Determine which compose file to use
    if [ "$USE_GPU" == "true" ]; then
        COMPOSE_FILE="docker/compose/docker-compose.cuda.yml"
    else
        COMPOSE_FILE="docker/compose/docker-compose.yml"
    fi
    
    # Stop existing containers
    docker-compose -f $COMPOSE_FILE down || true
    
    # Start new containers
    docker-compose -f $COMPOSE_FILE up -d
    
    log "Deployment completed"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait for application to start
    sleep 10
    
    # Check if containers are running
    cd "$PROJECT_ROOT"
    if [ "$USE_GPU" == "true" ]; then
        CONTAINERS=$(docker-compose -f docker/compose/docker-compose.cuda.yml ps -q)
    else
        CONTAINERS=$(docker-compose -f docker/compose/docker-compose.yml ps -q)
    fi
    
    for container in $CONTAINERS; do
        if ! docker ps -q --no-trunc | grep -q "$container"; then
            error "Container $container is not running"
        fi
    done
    
    # Check API health endpoint
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log "Health check passed"
            return 0
        fi
        warn "Health check attempt $i/30 failed, retrying in 5 seconds..."
        sleep 5
    done
    
    error "Health check failed after 30 attempts"
}

# Show logs
show_logs() {
    log "Showing application logs..."
    cd "$PROJECT_ROOT"
    if [ "$USE_GPU" == "true" ]; then
        docker-compose -f docker/compose/docker-compose.cuda.yml logs -f
    else
        docker-compose -f docker/compose/docker-compose.yml logs -f
    fi
}

# Main deployment process
main() {
    log "Starting deployment of $PROJECT_NAME version $VERSION"
    log "Docker directory: $DOCKER_DIR"
    log "Project root: $PROJECT_ROOT"
    
    check_prerequisites
    build_app
    deploy_app
    health_check
    
    log "Deployment completed successfully!"
    log "Application is available at: http://localhost:8000"
    log "API Documentation: http://localhost:8000/docs"
    log "Health Check: http://localhost:8000/health"
    
    if [ "$SHOW_LOGS" == "true" ]; then
        show_logs
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            USE_GPU="true"
            shift
            ;;
        --logs)
            SHOW_LOGS="true"
            shift
            ;;
        --registry)
            DOCKER_REGISTRY="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --gpu           Use GPU-accelerated deployment"
            echo "  --logs          Show logs after deployment"
            echo "  --registry URL  Docker registry URL"
            echo "  --version TAG   Version tag for the image"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Run main function
main