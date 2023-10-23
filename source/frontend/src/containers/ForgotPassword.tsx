// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from "react";
import {Auth} from "@aws-amplify/auth";

import {useNavigate} from "react-router-dom";
import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Grid,
  Header,
  Input,
  SpaceBetween
} from "@awsui/components-react";

const ForgotPassword = (props) => {
  let navigate = useNavigate();
  console.log(props);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [passwordError, setPasswordError] = useState(null);

  const handleForgotPassword = async () => {

    try {
      if(email) {
        await Auth.forgotPassword(email);
        setPasswordError("Check registered/verified email or phone number for password reset code.");
      }
    } catch (e) {
      setPasswordError(e.message);
    }
  }
  const handleSubmit = async event => {
    event.preventDefault();

    try {
      await Auth.forgotPasswordSubmit(email, code, password);
      navigate("/login");
    } catch (e) {
      setPasswordError(e.message)
    }
  }

  //Remove errors if user updates form data.
  useEffect(() => {
    setPasswordError(null);

  },[email, password, confirmPassword, email, code]);

  return(
    <Grid
      gridDefinition={[
        { colspan: { default: 12, xxs: 6 }, offset: { xxs: 3 } }
      ]}
    >
      <Box margin="xxl" padding="xxl">
        <Form
          header={
            <Header
              variant="h2"
            >
              Reset forgotten password
            </Header>
          }
          actions={
            // located at the bottom of the form
            <SpaceBetween direction="horizontal" size="xs">
              <Button disabled={!email} onClick={handleForgotPassword}>Request password reset code</Button>
              <Button disabled={!passwordError && email && code && password && confirmPassword && password === confirmPassword ? false : true} variant={'primary'} onClick={handleSubmit}>Reset password</Button>
              <Button onClick={() => navigate("/login")}>Cancel</Button>
            </SpaceBetween>
          }
          errorText={passwordError ? passwordError : null}
        >
          <Container

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
                  />
                </FormField>

                <FormField
                  key={'code'}
                  label={'Password reset code'}
                >
                  <Input
                    value={code}
                    onChange={event => setCode(event.detail.value)}
                    type="code"
                  />
                </FormField>

                <FormField
                  key={'password'}
                  label={'New password'}
                  errorText={password !== confirmPassword ? 'Passwords do not match.' : null}
                >
                  <Input
                    value={password}
                    onChange={event => setPassword(event.detail.value)}
                    type="password"
                  />
                </FormField>

                <FormField
                  key={'confirmPassword'}
                  label={'Confirm new password'}
                >
                  <Input
                    value={confirmPassword}
                    onChange={event => setConfirmPassword(event.detail.value)}
                    type="password"
                  />
                </FormField>
              </SpaceBetween>
            </SpaceBetween>
          </Container>
        </Form>
      </Box>
    </Grid>
  );

}

export default ForgotPassword
