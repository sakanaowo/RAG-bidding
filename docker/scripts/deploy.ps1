# Production deployment script for RAG-bidding application (PowerShell)
# This script handles the complete deployment process from the docker folder

param(
    [switch]$UseGPU,
    [switch]$ShowLogs,
    [string]$Registry = "localhost:5000",
    [string]$Version = "latest",
    [switch]$Help
)

# Configuration
$ProjectName = "rag-bidding"
$Environment = "production"
$DockerDir = $PSScriptRoot
$ProjectRoot = Split-Path $DockerDir -Parent

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"

function Write-Log {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] WARNING: $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] ERROR: $Message" -ForegroundColor $Red
    exit 1
}

# Show help
if ($Help) {
    Write-Host "Usage: .\deploy.ps1 [OPTIONS]"
    Write-Host "Options:"
    Write-Host "  -UseGPU         Use GPU-accelerated deployment"
    Write-Host "  -ShowLogs       Show logs after deployment"
    Write-Host "  -Registry URL   Docker registry URL"
    Write-Host "  -Version TAG    Version tag for the image"
    Write-Host "  -Help           Show this help message"
    exit 0
}

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed or not in PATH"
    }
    
    if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
        Write-Error "Docker Compose is not installed or not in PATH"
    }
    
    # Check for .env file in docker/config or project root
    $envFile = Join-Path $ProjectRoot ".env"
    $dockerEnvFile = Join-Path $DockerDir "config\.env"
    $exampleEnvFile = Join-Path $DockerDir "config\.env.example"
    $projectExampleEnvFile = Join-Path $ProjectRoot ".env.example"
    
    if (!(Test-Path $envFile) -and !(Test-Path $dockerEnvFile)) {
        Write-Warning ".env file not found. Creating from template..."
        if (Test-Path $exampleEnvFile) {
            Copy-Item $exampleEnvFile $envFile
        } elseif (Test-Path $projectExampleEnvFile) {
            Copy-Item $projectExampleEnvFile $envFile
        }
        Write-Warning "Please edit .env file with your configuration before proceeding"
        exit 1
    }
    
    Write-Log "Prerequisites check passed"
}

# Build application
function Build-App {
    Write-Log "Building application..."
    
    Set-Location $ProjectRoot
    
    # Determine which Dockerfile to use
    if ($UseGPU) {
        $Dockerfile = "docker/Dockerfile.cuda"
        $ComposeFile = "docker/compose/docker-compose.cuda.yml"
        Write-Log "Building with GPU support"
    } else {
        $Dockerfile = "docker/Dockerfile"
        $ComposeFile = "docker/compose/docker-compose.yml"
        Write-Log "Building with CPU support"
    }
    
    # Build the image
    docker build -f $Dockerfile -t "${ProjectName}:${Version}" .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
    }
    
    # Tag for registry if specified
    if ($Registry -ne "localhost:5000") {
        docker tag "${ProjectName}:${Version}" "${Registry}/${ProjectName}:${Version}"
    }
    
    Write-Log "Build completed successfully"
}

# Deploy application
function Deploy-App {
    Write-Log "Deploying application..."
    
    Set-Location $ProjectRoot
    
    # Determine which compose file to use
    if ($UseGPU) {
        $ComposeFile = "docker/compose/docker-compose.cuda.yml"
    } else {
        $ComposeFile = "docker/compose/docker-compose.yml"
    }
    
    # Stop existing containers
    docker-compose -f $ComposeFile down
    
    # Start new containers
    docker-compose -f $ComposeFile up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Deployment failed"
    }
    
    Write-Log "Deployment completed"
}

# Health check
function Test-Health {
    Write-Log "Performing health check..."
    
    # Wait for application to start
    Start-Sleep -Seconds 10
    
    # Check API health endpoint
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Log "Health check passed"
                return
            }
        } catch {
            Write-Warning "Health check attempt $i/30 failed, retrying in 5 seconds..."
            Start-Sleep -Seconds 5
        }
    }
    
    Write-Error "Health check failed after 30 attempts"
}

# Show logs
function Show-Logs {
    Write-Log "Showing application logs..."
    Set-Location $ProjectRoot
    if ($UseGPU) {
        docker-compose -f docker/compose/docker-compose.cuda.yml logs -f
    } else {
        docker-compose -f docker/compose/docker-compose.yml logs -f
    }
}

# Main deployment process
function Main {
    Write-Log "Starting deployment of $ProjectName version $Version"
    Write-Log "Docker directory: $DockerDir"
    Write-Log "Project root: $ProjectRoot"
    
    Test-Prerequisites
    Build-App
    Deploy-App
    Test-Health
    
    Write-Log "Deployment completed successfully!"
    Write-Log "Application is available at: http://localhost:8000"
    Write-Log "API Documentation: http://localhost:8000/docs"
    Write-Log "Health Check: http://localhost:8000/health"
    
    if ($ShowLogs) {
        Show-Logs
    }
}

# Run main function
Main