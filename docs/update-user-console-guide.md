# Update User Attributes via AWS Console

Since the IAM user has reached the inline policy limit, the easiest way to update user attributes is via the AWS Console.

## Steps to Update User Attributes

1. **Open AWS Cognito Console**

   - Go to: https://console.aws.amazon.com/cognito/
   - Make sure you're in the `us-east-1` region

2. **Navigate to User Pool**

   - Click on "User pools" in the left sidebar
   - Find and click on: `skyfi-intellicheck-user-pool-dev`

3. **Find the User**

   - Click on "Users" in the left sidebar
   - Search for: `ycorcos26@gmail.com`
   - Click on the user

4. **Edit User Attributes**

   - Scroll down to the "Attributes" section
   - Click "Edit" next to the attributes
   - Add/Update:
     - `given_name` = `Yahav`
     - `family_name` = `Corcos`
   - Click "Save changes"

5. **Verify**
   - The attributes should now show in the user's profile
   - The user needs to log out and log back in to get a fresh JWT token with the new attributes

## Alternative: Use Admin AWS Credentials

If you have admin AWS credentials, you can run:

```bash
cd infra
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

aws cognito-idp admin-update-user-attributes \
  --user-pool-id "$USER_POOL_ID" \
  --username "ycorcos26@gmail.com" \
  --user-attributes \
    Name=given_name,Value="Yahav" \
    Name=family_name,Value="Corcos" \
  --region us-east-1
```

## After Updating

Once the attributes are set:

1. Log out of the application
2. Log back in
3. You should see "YC" initials in the navbar (from Yahav Corcos)
