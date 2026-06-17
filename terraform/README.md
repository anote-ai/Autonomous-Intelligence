# Terraform — AWS deployment for Autonomous-Intelligence

Provisions: ECR repo, ECS Fargate cluster/service for the backend behind an ALB,
RDS MySQL, and an S3 + CloudFront distribution for the web frontend.
CloudFront routes `/api/*`, `/auth/*`, and `/health` to the backend ALB so the
React app can keep using same-origin relative paths in production, and
everything else to the S3 bucket holding the Vite build.

This stack deliberately uses the account's **default VPC** to keep the first
deploy simple. For a hardened production setup, swap `network.tf` for a real
VPC module with private subnets + NAT for ECS/RDS.

## One-time setup

1. Create an S3 bucket for Terraform state and uncomment/fill in the `backend "s3"`
   block in `versions.tf`, or pass `-backend-config` flags to `terraform init`.
2. `terraform init`
3. Provide secrets — never commit these. Use a `terraform.tfvars` file (gitignored)
   or `TF_VAR_*` environment variables:
   ```
   export TF_VAR_db_password="..."
   export TF_VAR_jwt_secret_key="..."
   export TF_VAR_anthropic_api_key="..."
   export TF_VAR_openai_api_key="..."
   export TF_VAR_stripe_secret_key="..."
   ```
4. `terraform plan` / `terraform apply`

## After the first apply

- Push a backend image to the ECR repo Terraform created (`ecr_repository_url` output),
  then either re-run `terraform apply -var backend_image_tag=<sha>` or let
  `.github/workflows/deploy.yml` roll it via `aws ecs update-service --force-new-deployment`.
- Sync the built frontend (`packages/web/dist`) to the S3 bucket (`s3_bucket_name` output)
  and invalidate CloudFront — `deploy.yml` already does both.
- Point your domain's DNS at the `cloudfront_domain_name` output (or set
  `domain_name` + `acm_certificate_arn` to use a custom domain with HTTPS).

## What this does NOT cover yet

- Redis / Tika sidecars (used by docker-compose locally) — add `aws_elasticache_cluster`
  and a second ECS service if those are needed in production.
- Multi-AZ / private subnets — current setup runs ECS tasks with public IPs in the
  default VPC's public subnets for simplicity.
- CI/CD bootstrapping of the Terraform state bucket itself (chicken-and-egg —
  create that bucket manually once, by hand).
