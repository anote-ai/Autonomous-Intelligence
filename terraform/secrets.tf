resource "aws_secretsmanager_secret" "backend" {
  name = "${var.project_name}-${var.environment}-backend-secrets"
}

resource "aws_secretsmanager_secret_version" "backend" {
  secret_id = aws_secretsmanager_secret.backend.id
  secret_string = jsonencode({
    JWT_SECRET_KEY    = var.jwt_secret_key
    DB_PASSWORD       = var.db_password
    ANTHROPIC_API_KEY = var.anthropic_api_key
    OPENAI_API_KEY    = var.openai_api_key
    STRIPE_SECRET_KEY = var.stripe_secret_key
  })
}
