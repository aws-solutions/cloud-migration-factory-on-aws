/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useState} from "react";
import { Auth } from "@aws-amplify/auth";
import {useLocation, useNavigate} from "react-router-dom";
import {
  Box,
  FormField,
  Input,
  Button, Header, SpaceBetween, Grid,
  Link, Form, Container, TextContent
} from '@awsui/components-react';

const Login = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMFACode] = useState('');
  const [userChallenge, setUserChallenge] = useState(null);
  const [getMFACode, setGetMFACode] = useState(false);
  const [loginError, setLoginError] = useState(null);

  const handleSubmit = async event => {
    event.preventDefault();

    setLoginError(null);
    let userAuthenticated = false;

    try {
      if (password === '' || email === '') {
        setLoginError('Incorrect username or password.');
      }
      else {
        const user = await Auth.signIn(email, password);

        if (user.challengeName === 'SMS_MFA' || user.challengeName === 'SOFTWARE_TOKEN_MFA') {
          setUserChallenge(user);
          setGetMFACode(true);
        } else if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
          navigate("/change/pwd");
        } else {
          userAuthenticated = true;
        }

        if(userAuthenticated){
          props.userHasAuthenticated(true);

          if(location.pathname !== '/login'){
            navigate(location.pathname);
          } else {
            navigate('/');
          }
        }
      }
    } catch (e) {
      if (e.message === 'User does not exist.') {
        setLoginError('Incorrect username or password.');
      }
      else {
        setLoginError(e.message);
      }
    }
  }

  const handleSubmitCode = async event => {
    event.preventDefault();

    let userAuthenticated = false;
    setLoginError(null);

    try {
      if (password === '' || email === '' || mfaCode === '') {
        setLoginError('Incorrect username, password or MFA Code.')
      }
      else {

        if (userChallenge.challengeName === 'SMS_MFA' || userChallenge.challengeName === 'SOFTWARE_TOKEN_MFA') {
          // If MFA is enabled, sign-in should be confirmed with the confirmation code
          await Auth.confirmSignIn(
            userChallenge,   // Return object from Auth.signIn()
            mfaCode,   // Confirmation code
            userChallenge.challengeName
          );
          userAuthenticated = true;

        } else if (userChallenge.challengeName === 'NEW_PASSWORD_REQUIRED') {
          navigate("/change/pwd");
        } else {
          userAuthenticated = true;
        }

        if(userAuthenticated){
          props.userHasAuthenticated(true);

          if(location.pathname !== '/login'){
            navigate(location.pathname);
          } else {
            navigate('/');
          }

        }
        await resetScreen();
      }
    } catch (e) {
      if (e.message === 'Invalid user.') {
        setLoginError('Incorrect username, password or code.')
      }
      else {
        setLoginError(e.message);
      }
    }
  }

  const resetScreen = async () => {
    setUserChallenge(null);
    setEmail('')
    setPassword('');
    setMFACode('');
    setGetMFACode(false);
    setLoginError(null);
  }

  const handleForgotPassword = async () => {
    navigate("/forgot/pwd");
  }

  return (
    <Grid
    gridDefinition={[
      { colspan: { default: 12, s: 5} },
    ]}
    >
      <div></div>
      <Box margin="xxl" padding="xxl" >
        <Container header={<Header variant="h1">{'AWS Cloud Migration Factory'}</Header>}>
          <SpaceBetween size={'xs'} direction={'vertical'}>
            <Container>
            <Form
              actions={
                // located at the bottom of the form
                <SpaceBetween direction="horizontal" size="xs">

                  <Button onClick={resetScreen} disabled={email && password ? false : true}>
                    Clear
                  </Button>
                  {getMFACode
                    ?
                      <Button onClick={handleSubmitCode} disabled={mfaCode ? false : true} variant="primary">
                        Confirm Code
                      </Button>
                    :
                    <Button onClick={handleSubmit} disabled={email && password ? false : true} variant="primary">
                      Login
                    </Button>
                  }
                </SpaceBetween>
              }
              errorText={loginError ? loginError : null}
            >
                  <SpaceBetween size={'xl'} direction={'vertical'}>
                    <SpaceBetween size={'xxs'} direction={'vertical'}>
                      <FormField
                        key={'username'}
                        label={'Username'}
                      >
                        <Input
                          value={email}
                          onChange={event => setEmail(event.detail.value)}
                          disabled={getMFACode}
                        />
                      </FormField>

                      <FormField
                        key={'password'}
                        label={'Password'}
                      >
                        <Input
                          value={password}
                          onChange={event => setPassword(event.detail.value)}
                          type="password"
                          disabled={getMFACode}
                        />
                      </FormField>
                      {getMFACode ?
                        <FormField
                          key={'mfaCode'}
                          label={'MFA Code'}
                        >
                          <Input
                            value={mfaCode}
                            onChange={event => setMFACode(event.detail.value)}
                          />
                        </FormField>
                        :
                        null
                      }
                    </SpaceBetween>
                    <Link onFollow={handleForgotPassword}>Forgot your password?</Link>
                  </SpaceBetween>
            </Form>
          </Container>
            {window.env.COGNITO_HOSTED_UI_URL ?
              <center>
                <SpaceBetween size={'xs'} direction={'vertical'}>
                  <Box textAlign={'center'}>
                    <TextContent>
                      <center>
                        <h3>Or</h3>
                      </center>
                    </TextContent>
                  </Box>
                  <Button disabled={email || password ? true : false} onClick={() => Auth.federatedSignIn()}>Sign in with your corporate ID</Button>
                </SpaceBetween>
              </center>
            :
              null
            }
          </SpaceBetween>
        </Container>
      </Box>
      <div></div>
    </Grid>

  )

}

export default Login