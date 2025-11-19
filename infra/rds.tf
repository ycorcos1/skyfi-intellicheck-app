# RDS Subnet Group
resource "aws_db_subnet_group" "intellicheck" {
  name       = "skyfi-intellicheck-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "skyfi-intellicheck-db-subnet-group"
  }
}

# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "intellicheck" {
  identifier     = "skyfi-intellicheck-db-${var.environment}"
  engine         = "postgres"
  engine_version = "15.4"

  # Ignore engine_version changes to prevent downgrade attempts
  lifecycle {
    ignore_changes = [engine_version]
  }
  instance_class    = var.db_instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  db_name           = "intellicheck"
  username          = "intellicheck_admin"
  password          = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.intellicheck.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az                  = var.environment == "prod" ? true : false
  backup_retention_period   = 7
  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "skyfi-intellicheck-db-final-snapshot" : null

  storage_encrypted = true

  tags = {
    Name = "skyfi-intellicheck-db"
  }
}

# Store credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "skyfi-intellicheck-db-credentials-${var.environment}"

  tags = {
    Name = "skyfi-intellicheck-db-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = aws_db_instance.intellicheck.username
    password = random_password.db_password.result
    host     = aws_db_instance.intellicheck.address
    port     = aws_db_instance.intellicheck.port
    dbname   = aws_db_instance.intellicheck.db_name
    engine   = "postgres"
    db_url   = "postgresql://${aws_db_instance.intellicheck.username}:${random_password.db_password.result}@${aws_db_instance.intellicheck.address}:${aws_db_instance.intellicheck.port}/${aws_db_instance.intellicheck.db_name}"
  })
}

