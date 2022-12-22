/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from "react";
import { Auth } from "aws-amplify";

import {useLocation, useNavigate, useParams} from "react-router-dom";
import {Box, Button, Container, Form, FormField, Header, Input, SpaceBetween} from "@awsui/components-react";

const ChangePassword = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState(null);

  const handleSubmit = async event => {
    event.preventDefault();

    setIsLoading(true);

    try {
      const user = await Auth.signIn(email, oldPassword);

      if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
        //? What is this? const { requiredAttributes } = user.challengeParam; // the array of required attributes, e.g ['email', 'phone_number']
        await Auth.completeNewPassword(user, newPassword);
      }
      else {
        const authUser = await Auth.currentAuthenticatedUser();
        await Auth.changePassword(authUser, oldPassword, newPassword);
      }
      navigate("/");
    } catch (e) {
      if (e.message === 'User does not exist.') {
        setPasswordError('Incorrect username or password.');
      }
      else{
        setPasswordError('An unexpected error occurred.');
      }
      setIsLoading(false);
    }
  }

  //Remove errors if user updates form data.
  useEffect(() => {
    setPasswordError(null);

  },[email, oldPassword, newPassword]);

  return (
    <Box margin="xxl" padding="xxl">
      <Form
        header={
          <Header
            variant="h1"
          >
            Change Password
          </Header>
        }
        actions={
          // located at the bottom of the form
          <SpaceBetween direction="horizontal" size="xs">
            <Button disabled={!passwordError && email && oldPassword && newPassword && confirmPassword && newPassword === confirmPassword ? false : true} variant={'primary'} loading={isLoading} onClick={handleSubmit}>Change Password</Button>
            <Button onClick={() => navigate("/")}>Cancel</Button>
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
                key={'oldPassword'}
                label={'Current password'}
              >
                <Input
                  value={oldPassword}
                  onChange={event => setOldPassword(event.detail.value)}
                  type="password"
                />
              </FormField>

              <FormField
                key={'password'}
                label={'New password'}
                errorText={newPassword !== confirmPassword ? 'Passwords do not match.' : null}
              >
                <Input
                  value={newPassword}
                  onChange={event => setNewPassword(event.detail.value)}
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
  );

}

export default ChangePassword
