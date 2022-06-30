import React, {useState} from "react";
import { Auth } from "aws-amplify";
import {useLocation, useNavigate, useParams} from "react-router-dom";
import {
  Box,
  FormField,
  Input,
  Button, Header, SpaceBetween, Grid,
  Link, Form, Container
} from '@awsui/components-react';
import {getNestedValuePath} from "../resources/main";

const Login = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMFACode] = useState('');
  const [userChallenge, setUserChallenge] = useState(null);
  const [getMFACode, setGetMFACode] = useState(false);
  const [loginError, setLoginError] = useState(null);

  function validateForm() {
    return email.length > 0 && password.length > 0;
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
    }
  }

  function getCodeFromUserInput(){
    const code = prompt("One Time Access Code?");
    return code
  }

  const handleSubmit = async event => {
    event.preventDefault();

    setIsLoading(true);
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
          userAuthenticated = false;
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
      setIsLoading(false);
    }
  }

  const handleSubmitCode = async event => {
    event.preventDefault();

    setIsLoading(true);
    let userAuthenticated = false;
    setLoginError(null);

    try {
      if (password === '' || email === '' || mfaCode === '') {
        setLoginError('Incorrect username, password or MFA Code.')
      }
      else {

        if (userChallenge.challengeName === 'SMS_MFA' || userChallenge.challengeName === 'SOFTWARE_TOKEN_MFA') {
          // If MFA is enabled, sign-in should be confirmed with the confirmation code
          const loggedUser = await Auth.confirmSignIn(
            userChallenge,   // Return object from Auth.signIn()
            mfaCode,   // Confirmation code
            userChallenge.challengeName
          );
          userAuthenticated = true;

        } else if (userChallenge.challengeName === 'NEW_PASSWORD_REQUIRED') {
          navigate("/change/pwd");
          userAuthenticated = false;
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
      setIsLoading(false);
    }
  }

  const resetScreen = async () => {
    //event.preventDefault();

    setIsLoading(true);
    setUserChallenge(null);
    setEmail('')
    setPassword('');
    setMFACode('');
    setGetMFACode(false);
    setLoginError(null);
  }

  const handleForgotPassword = async () => {
    //event.preventDefault();

    setIsLoading(true);

    try {
      if(email) {
        await Auth.forgotPassword(email);
      } else {
        navigate("/forgot/pwd");
      }
    } catch (e) {
      alert(e.message);
      setIsLoading(false);
    }
  }

  return (
    <Grid
    gridDefinition={[
      { colspan: { default: 12, xxs: 6 }, offset: { xxs: 3 } }
    ]}
  >
    <Box margin="xxl" padding="xxl">
      <Container>
        <Form
          header={<Header variant="h1">{'AWS Cloud Migration Factory'}</Header>}
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
    </Box>
    </Grid>

  )

}

export default Login