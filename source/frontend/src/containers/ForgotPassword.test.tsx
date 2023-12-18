import {render, screen} from "@testing-library/react";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {NO_SESSION, SessionContext} from "../contexts/SessionContext";
import React from "react";
import userEvent from "@testing-library/user-event";
import {Auth} from "@aws-amplify/auth";
import ForgotPassword from "./ForgotPassword";

function renderForgotPasswordPage() {
  return render(
    <MemoryRouter initialEntries={['/forgot/pwd']}>
      <SessionContext.Provider value={NO_SESSION}>
        <div id='modal-root'/>
        <Routes>
          <Route path={'/forgot/pwd'} element={<ForgotPassword></ForgotPassword>}> </Route>
          <Route path={'/login'} element={<>This is the login page</>}> </Route>
        </Routes>
      </SessionContext.Provider>
    </MemoryRouter>
  );
}

test('it renders the forgot password page with disabled buttons', async () => {
  // WHEN
  renderForgotPasswordPage();

  // THEN
  expect(await screen.findByRole('heading', {name: /Reset forgotten password/i})).toBeInTheDocument();
  expect(await screen.findByRole('textbox', {name: /Username/i})).toBeInTheDocument();
  expect(await screen.findByRole('textbox', {name: /Password reset code/i})).toBeInTheDocument();
  expect(screen.getByLabelText("New password")).toBeInTheDocument();
  expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();

  expect(await screen.findByRole('button', {name: /Request password reset code/i})).toBeDisabled();
  expect(await screen.findByRole('button', {name: /Reset password/i})).toBeDisabled();
  expect(await screen.findByRole('button', {name: /Cancel/i})).toBeEnabled();

  // AND WHEN
  await userEvent.click(screen.getByRole('button', {name: /Cancel/i}));

  // THEN
  expect(await screen.findByText(/This is the login page/i)).toBeInTheDocument();
});

test('it sends a reset code', async () => {
  // GIVEN
  const sendForgotPasswordMockFn = jest.fn();
  jest.spyOn(Auth, 'forgotPassword').mockImplementation(sendForgotPasswordMockFn);
  renderForgotPasswordPage();

  // WHEN
  await userEvent.type(await screen.findByRole('textbox', {name: /Username/i}), 'some-username');

  // THEN
  const sendCodeButton = await screen.findByRole('button', {name: /Request password reset code/i});
  expect(sendCodeButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(sendCodeButton);

  // THEN
  expect(sendForgotPasswordMockFn).toHaveBeenCalledWith('some-username');
  expect(await screen.findByText(
    'Check registered/verified email or phone number for password reset code.'
  )).toBeInTheDocument();
});

test('it resets the password', async () => {
  // GIVEN
  const submitMockFn = jest.fn();
  jest.spyOn(Auth, 'forgotPasswordSubmit').mockImplementation(submitMockFn);
  renderForgotPasswordPage();

  // WHEN
  await userEvent.type(await screen.findByRole('textbox', {name: /Username/i}), 'some-username');
  await userEvent.type(await screen.findByRole('textbox', {name: /Password reset code/i}), 'some-code');
  await userEvent.type(screen.getByLabelText("New password"), 'some-new-password');
  await userEvent.type(screen.getByLabelText("Confirm new password"), 'some-new-password');

  // THEN
  const resetPasswordButton = screen.getByRole('button', {name: /Reset password/i});
  expect(resetPasswordButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(resetPasswordButton);

  // THEN
  expect(submitMockFn).toHaveBeenCalledWith('some-username', 'some-code', 'some-new-password');
  expect(await screen.findByText(/This is the login page/i)).toBeInTheDocument();
});
