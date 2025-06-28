#!/bin/bash
set -e

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "🔧 Loading environment from .env file..."
    set -a
    source .env
    set +a
fi

PROJECT_ID=${PROJECT_ID:-""}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="usda-nutrition-mcp"
REPOSITORY="usda-nutrition"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"

echo "🚀 USDA Nutrition MCP - GCP Cloud Run Deployment (Artifact Registry)"

# Get project ID
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

echo "✅ Using project: $PROJECT_ID"
echo "✅ API key configured: ${FDC_API_KEY:0:8}..."
echo "✅ Using image: $IMAGE_NAME"

# Set project
gcloud config set project $PROJECT_ID

# Enable APIs
echo "🔧 Enabling GCP APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Verify repository exists
echo "📦 Verifying Artifact Registry repository..."
if gcloud artifacts repositories describe $REPOSITORY --location=$REGION --project=$PROJECT_ID &> /dev/null; then
    echo "✅ Repository '$REPOSITORY' exists"
else
    echo "❌ Repository '$REPOSITORY' not found. Please create it manually in the GCP Console first."
    echo "   Go to: https://console.cloud.google.com/artifacts"
    echo "   Create repository with name: $REPOSITORY, format: Docker, location: $REGION"
    exit 1
fi

# Create/update secret
echo "🔑 Managing API key secret..."
if gcloud secrets describe usda-api-key --project=$PROJECT_ID &> /dev/null; then
    echo -n "$FDC_API_KEY" | gcloud secrets versions add usda-api-key --data-file=- --project=$PROJECT_ID
else
    echo -n "$FDC_API_KEY" | gcloud secrets create usda-api-key --data-file=- --project=$PROJECT_ID
fi

# Grant Cloud Run service account access to the secret
echo "🔐 Setting up Secret Manager permissions..."
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Project Number: $PROJECT_NUMBER"
echo "Service Account: $SERVICE_ACCOUNT"

# Grant the secret accessor role
gcloud secrets add-iam-policy-binding usda-api-key \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# Configure Docker
echo "🐳 Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
echo "🏗️  Building and pushing..."
docker build -f deployment/Dockerfile -t $IMAGE_NAME:latest .
docker push $IMAGE_NAME:latest

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME:latest \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=10 \
    --min-instances=0 \
    --timeout=300 \
    --set-env-vars=ENVIRONMENT=production \
    --update-secrets=FDC_API_KEY=usda-api-key:latest \
    --project=$PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🧪 Test: curl $SERVICE_URL/health"
echo "📚 Docs: $SERVICE_URL/docs"