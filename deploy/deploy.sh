#!/usr/bin/env bash
# Build -> push ไป Amazon ECR -> สั่ง ECS Fargate ดึง image ใหม่
# ต้องติดตั้ง AWS CLI v2 + Docker และรัน `aws configure` ก่อน
set -euo pipefail

REGION=${AWS_REGION:-ap-southeast-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO=teamup-frontend
CLUSTER=${ECS_CLUSTER:-teamup-cluster}
SERVICE=${ECS_SERVICE:-teamup-frontend-service}
TAG=$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)
IMAGE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO"

echo "1) สร้าง ECR repository (ถ้ายังไม่มี)"
aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" --region "$REGION" >/dev/null

echo "2) Login Docker เข้า ECR"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

echo "3) Build image (linux/amd64 ให้ตรงกับ Fargate แม้ build บน Mac M1/M2)"
docker build --platform linux/amd64 -t "$IMAGE:$TAG" -t "$IMAGE:latest" .

echo "4) Push"
docker push "$IMAGE:$TAG"
docker push "$IMAGE:latest"

echo "5) สั่ง ECS service deploy ใหม่"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --force-new-deployment --region "$REGION" >/dev/null
echo "Done: $IMAGE:$TAG"
