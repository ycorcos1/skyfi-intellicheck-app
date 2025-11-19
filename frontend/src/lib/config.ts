export const config = {
  cognito: {
    region: process.env.NEXT_PUBLIC_COGNITO_REGION ?? "us-east-1",
    userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID ?? "",
    clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? "",
  },
  api: {
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
} as const;


