import {render, screen} from "@testing-library/react";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {NO_SESSION, SessionContext} from "../contexts/SessionContext";
import React from "react";
import Login from "./Login";
import userEvent from "@testing-library/user-event";
import {Auth} from "@aws-amplify/auth";

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <SessionContext.Provider value={NO_SESSION}>
        <div id='modal-root'/>
        <Routes>
          <Route path={'/login'} element={<Login/>}> </Route>
          <Route path={'/change/pwd'} element={<>This is the change password page</>}> </Route>
          <Route path={'/forgot/pwd'} element={<>This is the forgot password page</>}> </Route>
          <Route path={'/'} element={<>This is the authenticated landing page</>}> </Route>
        </Routes>
      </SessionContext.Provider>
    </MemoryRouter>
  );
}

test('it clears username and password when `clear` button is clicked', async () => {
  // WHEN
  renderLoginPage();

  // THEN
  expect(await screen.findByRole('heading', {name: /aws cloud migration factory/i})).toBeInTheDocument();
  expect(await screen.findByLabelText('Username')).toBeInTheDocument();
  expect(await screen.findByLabelText('Password')).toBeInTheDocument();

  expect(await screen.findByRole('button', {name: /forgot your password?/i})).toBeInTheDocument();
  expect(await screen.findByRole('button', {name: /login/i})).toBeDisabled();
  expect(await screen.findByRole('button', {name: /clear/i})).toBeDisabled();

  // AND WHEN entering some username and password
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');

  // THEN
  expect(await screen.findByRole('button', {name: /login/i})).toBeEnabled();
  expect(await screen.findByRole('button', {name: /clear/i})).toBeEnabled();

  // AND WHEN clicking the clear button
  await userEvent.click(screen.getByRole('button', {name: /clear/i}));

  // THEN
  expect(screen.getByRole('textbox', {name: /username/i})).toHaveValue('');
  expect(screen.getByLabelText(/password/i)).toHaveValue('');
});

test('it shows error message when login fails', async () => {
  // GIVEN
  jest.spyOn(Auth, 'signIn').mockImplementation(() => {
    throw new Error('some-error')
  });
  renderLoginPage();

  // WHEN
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');
  await userEvent.click(screen.getByRole('button', {name: /login/i}));

  // THEN
  expect((await screen.findAllByText(/some-error/i))[0]).toBeInTheDocument();
});

test('it navigates to the `change password` page when user clicks `forgot password`', async () => {
  // GIVEN
  const cognitoUser = {challengeName: 'NEW_PASSWORD_REQUIRED'};
  jest.spyOn(Auth, 'signIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  renderLoginPage();

  // WHEN
  await userEvent.click(await screen.findByRole('button', {name: /forgot your password?/i}));

  // THEN
  expect(await screen.findByText('This is the forgot password page')).toBeInTheDocument();
});

test('it navigates to the `change password` page when Cognito requires a password change', async () => {
  // GIVEN
  const cognitoUser = {challengeName: 'NEW_PASSWORD_REQUIRED'};
  jest.spyOn(Auth, 'signIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  renderLoginPage();

  // WHEN
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');
  await userEvent.click(screen.getByRole('button', {name: /login/i}));

  // THEN
  expect(await screen.findByText('This is the change password page')).toBeInTheDocument();
});

test('it navigates to the home page when login succeeds', async () => {
  // GIVEN
  const cognitoUser = {};
  jest.spyOn(Auth, 'signIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  renderLoginPage();

  // WHEN
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');
  await userEvent.click(screen.getByRole('button', {name: /login/i}));

  // THEN
  expect(await screen.findByText('This is the authenticated landing page')).toBeInTheDocument();
});

test('it asks for MFA token when Cognito requires MFA', async () => {
  // GIVEN
  const cognitoUser = {challengeName: 'SOFTWARE_TOKEN_MFA'};
  jest.spyOn(Auth, 'signIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  jest.spyOn(Auth, 'confirmSignIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  renderLoginPage();

  // WHEN
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');
  await userEvent.click(screen.getByRole('button', {name: /login/i}));

  // THEN
  const mfaInput = await screen.findByRole('textbox', {name: /mfa code/i});
  expect(mfaInput).toBeInTheDocument();
  const confirmButton = await screen.findByRole('button', {name: /Confirm Code/i});
  expect(confirmButton).toBeDisabled();

  // AND WHEN entering the MFA token
  await userEvent.type(mfaInput, 'some-code');
  await userEvent.click(confirmButton);

  // THEN
  expect(await screen.findByText('This is the authenticated landing page')).toBeInTheDocument();
});

test('it shows an error if MFA token is invalid', async () => {
  // GIVEN
  const cognitoUser = {challengeName: 'SOFTWARE_TOKEN_MFA'};
  jest.spyOn(Auth, 'signIn').mockImplementation(() => (Promise.resolve(cognitoUser)));
  jest.spyOn(Auth, 'confirmSignIn').mockImplementation(() => {
    throw new Error('some-error')
  });
  renderLoginPage();

  // WHEN
  await userEvent.type(screen.getByRole('textbox', {name: /username/i}), 'some-username');
  await userEvent.type(screen.getByLabelText(/password/i), 'some-password');
  await userEvent.click(screen.getByRole('button', {name: /login/i}));

  // THEN
  const mfaInput = await screen.findByRole('textbox', {name: /mfa code/i});
  expect(mfaInput).toBeInTheDocument();
  const confirmButton = await screen.findByRole('button', {name: /Confirm Code/i});
  expect(confirmButton).toBeDisabled();

  // AND WHEN entering the MFA token
  await userEvent.type(mfaInput, 'some-code');
  await userEvent.click(confirmButton);

  // THEN
  expect((await screen.findAllByText(/some-error/i))[0]).toBeInTheDocument();
});
