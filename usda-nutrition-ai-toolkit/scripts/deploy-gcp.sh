#!/bin/bash
set -e

PROJECT_ID=${PROJECT_ID:-""}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="usda-nutrition-mcp"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 USDA Nutrition MCP - GCP Cloud Run Deployment"

# Get project ID if not set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi

echo "✅ Using project: $PROJECT_ID"


# Check API key
if [ -z "$FDC_API_KEY" ]; then
    echo "❌ FDC_API_KEY not set. Export it first: export FDC_API_KEY=your_key"
    exit 1
fi

echo "✅ API key configured"

# Enable APIs
echo "🔧 Enabling GCP APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create/update secret
echo "🔑 Managing API key secret..."
if gcloud secrets describe usda-api-key --project=$PROJECT_ID &> /dev/null; then
    echo -n "$FDC_API_KEY" | gcloud secrets versions add usda-api-key --data-file=- --project=$PROJECT_ID
else
    echo -n "$FDC_API_KEY" | gcloud secrets create usda-api-key --data-file=- --project=$PROJECT_ID
fi

# Configure Docker
gcloud auth configure-docker

# Build and push
echo "🏗️  Building and pushing image..."
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
EOF
