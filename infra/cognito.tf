# Cognito User Pool for SkyFi IntelliCheck authentication
resource "aws_cognito_user_pool" "intellicheck" {
  name = "skyfi-intellicheck-user-pool-${var.environment}"

  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false
  }

  # Note: given_name and family_name are standard Cognito attributes
  # They are available by default and don't need to be defined in the schema
  # They can be set via AdminUpdateUserAttributes and will appear in JWT tokens

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # Tags are applied via provider default_tags to avoid TagResource permission requirement
}

# Cognito App Client for API authentication
resource "aws_cognito_user_pool_client" "intellicheck" {
  name         = "skyfi-intellicheck-app-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.intellicheck.id

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH", # Required for amazon-cognito-identity-js library
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
  enable_token_revocation       = true
  generate_secret               = false

  id_token_validity      = 60
  access_token_validity  = 60
  refresh_token_validity = 30

  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }
}



