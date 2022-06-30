import React, {useState} from "react";
import {Auth} from "aws-amplify";

import {useNavigate} from "react-router-dom";
import {Box, Button, Container, FormField, Grid, Header, Input, Link, SpaceBetween} from "@awsui/components-react";

const ForgotPassword = (props) => {
  let navigate = useNavigate();

  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');

  function validateForm() {
    return email.length > 0 && password.length > 0 && code.length > 0;
  }

  const handleChange = event => {
    switch(event.target.id) {
      case 'email': {
        setEmail(event.target.value)
        break;
      }
      case 'password': {
        setPassword(event.target.value)
        break;
      }
      case 'code': {
        setCode(event.target.value)
        break;
      }
    }
  }

  const handleSubmit = async event => {
    event.preventDefault();

    setIsLoading(true);

    try {
      await Auth.forgotPasswordSubmit(email, code, password);
      alert("Password saved successfully!");
      navigate("/login");
    } catch (e) {
      alert(e.message);
      setIsLoading(false);
    }
  }

  return(
    <Grid
      gridDefinition={[
        { colspan: { default: 12, xxs: 6 }, offset: { xxs: 3 } }
      ]}
    >
      <Box margin="xxl" padding="xxl">
        <Container
          header={
            <Header
              variant="h2"
            >
              AWS Cloud Migration Factory - Reset Password
            </Header>
          }
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
                label={'Password Reset Code'}
              >
                <Input
                  value={code}
                  onChange={event => setCode(event.detail.value)}
                  type="code"
                />
              </FormField>

              <FormField
                key={'password'}
                label={'New Password'}
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
                label={'Confirm New Password'}
              >
                <Input
                  value={confirmPassword}
                  onChange={event => setConfirmPassword(event.detail.value)}
                  type="password"
                />
              </FormField>
            </SpaceBetween>
            <Box float={'right'}>
            <SpaceBetween size={'xs'} direction={'horizontal'}>
              <Button disabled={email && code && password && confirmPassword && password === confirmPassword ? false : true} variant={'primary'} onClick={handleSubmit}>Reset Password</Button>
              <Button onClick={() => navigate("/login")}>Cancel</Button>
            </SpaceBetween>
            </Box>
          </SpaceBetween>
        </Container>
      </Box>
    </Grid>
  );

}

export default ForgotPassword
