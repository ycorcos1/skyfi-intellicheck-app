"use client";

import {
  AuthenticationDetails,
  CognitoRefreshToken,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession,
} from "amazon-cognito-identity-js";
import { config } from "./config";

function assertCognitoConfig() {
  if (!config.cognito.userPoolId || !config.cognito.clientId) {
    throw new Error(
      "Cognito configuration is missing. Ensure NEXT_PUBLIC_COGNITO_USER_POOL_ID and NEXT_PUBLIC_COGNITO_CLIENT_ID are set.",
    );
  }
}

let cachedPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool {
  if (cachedPool) {
    return cachedPool;
  }

  assertCognitoConfig();

  cachedPool = new CognitoUserPool({
    UserPoolId: config.cognito.userPoolId,
    ClientId: config.cognito.clientId,
  });

  return cachedPool;
}

export async function signIn(
  email: string,
  password: string,
): Promise<{ session: CognitoUserSession; user: CognitoUser }> {
  const userPool = getUserPool();

  const authenticationDetails = new AuthenticationDetails({
    Username: email,
    Password: password,
  });

  const user = new CognitoUser({
    Username: email,
    Pool: userPool,
  });

  return new Promise((resolve, reject) => {
    user.authenticateUser(authenticationDetails, {
      onSuccess: (session) => resolve({ session, user }),
      onFailure: (error) => reject(error),
      newPasswordRequired: () =>
        reject(new Error("New password challenge is not supported in this flow.")),
    });
  });
}

export function signOut() {
  const user = getUserPool().getCurrentUser();
  if (user) {
    user.signOut();
  }
}

export function getCurrentSession(): Promise<CognitoUserSession | null> {
  return new Promise((resolve, reject) => {
    const user = getUserPool().getCurrentUser();

    if (!user) {
      resolve(null);
      return;
    }

    user.getSession((error: Error | null, session: CognitoUserSession | null) => {
      if (error || !session) {
        reject(error ?? new Error("Unable to retrieve session."));
        return;
      }

      resolve(session);
    });
  });
}

export function refreshSession(): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    const user = getUserPool().getCurrentUser();

    if (!user) {
      reject(new Error("No authenticated user available."));
      return;
    }

    user.getSession((error: Error | null, session: CognitoUserSession | null) => {
      if (error || !session) {
        reject(error ?? new Error("Unable to retrieve session for refresh."));
        return;
      }

      const refreshToken = session.getRefreshToken();

      user.refreshSession(
        refreshToken as CognitoRefreshToken,
        (refreshError: Error | null, refreshedSession: CognitoUserSession | null) => {
          if (refreshError || !refreshedSession) {
            reject(refreshError ?? new Error("Failed to refresh session."));
            return;
          }

          resolve(refreshedSession);
        },
      );
    });
  });
}

