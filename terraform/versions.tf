terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Configure via `terraform init -backend-config=...` or a backend.hcl file.
    # Example:
    #   bucket = "anote-terraform-state"
    #   key    = "autonomous-intelligence/terraform.tfstate"
    #   region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}
