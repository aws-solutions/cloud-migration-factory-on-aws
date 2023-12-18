// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import {createContext, ReactNode, useEffect, useState} from "react";
import {Auth} from "@aws-amplify/auth";
import {Hub, HubCapsule} from '@aws-amplify/core';
import {CognitoUserSession} from "amazon-cognito-identity-js";
import {PreAuthApp} from "../PreAuthRoutes";

/**
 * SessionContext keeps track of the current session.
 * By providing the session information in a React.Context,
 * we can decouple individual components from @aws-amplify/auth
 * and easily inject a mock context in unit tests.
 */
export type SessionState = {
  idToken: string,
  accessToken: string | null,
  userName: string,
  userGroups: string[]
}

export const NO_SESSION: SessionState = {
  accessToken: '',
  idToken: '',
  userName: '',
  userGroups: []
};

export const SessionContext = createContext<SessionState>(NO_SESSION);

export const SessionContextProvider = ({children: app}: { children: ReactNode }) => {

  const [sessionState, setSessionState] = useState<{
    accessToken: string | null,
    idToken: string | null,
    userName: string | null,
    userGroups: string[]
  }>(NO_SESSION);

  useEffect(() => {
    const fetchSessionData = () => {
      Auth.currentSession().then(session => {
        setSessionState(getDataFromToken(session));
      }).catch(() => {
        console.log('No current user')
      });
    };

    const stopListening = Hub.listen('auth', (hubCapsule: HubCapsule) => {
      switch (hubCapsule.payload.event) {
        case 'signOut':
          setSessionState(NO_SESSION);
          break;
        case 'cognitoHostedUI':
          console.debug('Sign-in Hosted');
          fetchSessionData();
          break;
        case 'signIn':
          console.debug('Sign-in normal');
          fetchSessionData();
          break;
        case 'signIn_failure':
          console.debug('Sign-in failure', hubCapsule.payload);
          break;
        case 'cognitoHostedUI_failure':
          console.debug('Sign-in failure Hosted', hubCapsule.payload);
          break;
      }
    });

    // in case there is already a currentSession() when the app is loaded
    fetchSessionData();

    // cleanup the listener when the component unmounts
    return () => {
      stopListening();
    };
  }, []);

  // if no user is logged in, render the PreAuthApp instead of the children
  if (!sessionState.idToken) {
    return <PreAuthApp></PreAuthApp>
  }

  // only if a user is logged in, render the actual app and provide the session data as context
  return (
    <SessionContext.Provider value={{
      ...sessionState,
      idToken: sessionState.idToken,
      userName: sessionState.userName || 'User',
    }}>
      {app}
    </SessionContext.Provider>
  )
}

function decodeJwt(token: string) {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace('-', '+').replace('_', '/');
  return JSON.parse(window.atob(base64));
}

function getDataFromToken(session: CognitoUserSession): SessionState {
  console.log('get data from token')
  const idToken = session.getIdToken().getJwtToken();
  const accessToken = session.getAccessToken().getJwtToken();

  let decodedIdToken = decodeJwt(idToken);

  return {
    idToken,
    accessToken,
    userName: decodedIdToken.email || decodedIdToken['cognito:username'] || '',
    userGroups: decodedIdToken['cognito:groups'] || []
  }
}
