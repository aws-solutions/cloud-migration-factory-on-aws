import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { NO_SESSION, SessionContext } from "../contexts/SessionContext";
import React from "react";
import userEvent from "@testing-library/user-event";
import { Auth } from "@aws-amplify/auth";
import ChangePassword from "./ChangePassword";

function renderChangePasswordPage() {
  return render(
    <MemoryRouter initialEntries={["/forgot/pwd"]}>
      <SessionContext.Provider value={NO_SESSION}>
        <div id="modal-root" />
        <Routes>
          <Route path={"/forgot/pwd"} element={<ChangePassword></ChangePassword>}>
            {" "}
          </Route>
          <Route path={"/"} element={<>This is the login page</>}>
            {" "}
          </Route>
        </Routes>
      </SessionContext.Provider>
    </MemoryRouter>
  );
}

test("it renders the change password page with disabled buttons", async () => {
  // WHEN
  renderChangePasswordPage();

  // THEN
  expect(await screen.findByRole("heading", { name: /Change password/i })).toBeInTheDocument();
  expect(await screen.findByRole("textbox", { name: /Username/i })).toBeInTheDocument();
  expect(screen.getByLabelText("Current password")).toBeInTheDocument();
  expect(screen.getByLabelText("New password")).toBeInTheDocument();
  expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();

  expect(await screen.findByRole("button", { name: /Change password/i })).toBeDisabled();
  expect(await screen.findByRole("button", { name: /Cancel/i })).toBeEnabled();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: /Cancel/i }));

  // THEN
  expect(await screen.findByText(/This is the login page/i)).toBeInTheDocument();
});

test("it changes the password on first login", async () => {
  // GIVEN
  const cognitoUser = {
    challengeName: "NEW_PASSWORD_REQUIRED",
  };
  jest.spyOn(Auth, "signIn").mockImplementation(() => Promise.resolve(cognitoUser));
  jest.spyOn(Auth, "currentAuthenticatedUser").mockImplementation(() => Promise.resolve({}));
  const submitMockFn = jest.fn();
  jest.spyOn(Auth, "completeNewPassword").mockImplementation(submitMockFn);
  renderChangePasswordPage();

  // WHEN
  await userEvent.type(await screen.findByRole("textbox", { name: /Username/i }), "some-username");
  await userEvent.type(screen.getByLabelText("Current password"), "some-current-password");
  await userEvent.type(screen.getByLabelText("New password"), "some-new-password");
  await userEvent.type(screen.getByLabelText("Confirm new password"), "some-new-password");

  // THEN
  const changePasswordButton = screen.getByRole("button", { name: /Change password/i });
  expect(changePasswordButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(changePasswordButton);

  // THEN
  expect(submitMockFn).toHaveBeenCalledWith(cognitoUser, "some-new-password");
  expect(await screen.findByText(/This is the login page/i)).toBeInTheDocument();
});

test("it changes the password on users initiative", async () => {
  // GIVEN
  jest.spyOn(Auth, "signIn").mockImplementation(() => Promise.resolve({}));
  jest.spyOn(Auth, "currentAuthenticatedUser").mockImplementation(() => Promise.resolve({}));
  const submitMockFn = jest.fn();
  jest.spyOn(Auth, "changePassword").mockImplementation(submitMockFn);
  renderChangePasswordPage();

  // WHEN
  await userEvent.type(await screen.findByRole("textbox", { name: /Username/i }), "some-username");
  await userEvent.type(screen.getByLabelText("Current password"), "some-current-password");
  await userEvent.type(screen.getByLabelText("New password"), "some-new-password");
  await userEvent.type(screen.getByLabelText("Confirm new password"), "some-new-password");

  // THEN
  const changePasswordButton = screen.getByRole("button", { name: /Change password/i });
  expect(changePasswordButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(changePasswordButton);

  // THEN
  expect(submitMockFn).toHaveBeenCalledWith({}, "some-current-password", "some-new-password");
  expect(await screen.findByText(/This is the login page/i)).toBeInTheDocument();
});

test("it shows an error message when the current password is incorrect", async () => {
  // GIVEN
  jest.spyOn(Auth, "signIn").mockImplementation(() => Promise.resolve({}));
  jest.spyOn(Auth, "currentAuthenticatedUser").mockImplementation(() => Promise.resolve({}));
  jest.spyOn(Auth, "changePassword").mockImplementation(() => {
    throw new Error("some-error");
  });
  renderChangePasswordPage();

  // WHEN
  await userEvent.type(await screen.findByRole("textbox", { name: /Username/i }), "some-username");
  await userEvent.type(screen.getByLabelText("Current password"), "some-current-password");
  await userEvent.type(screen.getByLabelText("New password"), "some-new-password");
  await userEvent.type(screen.getByLabelText("Confirm new password"), "some-new-password");

  // THEN
  const changePasswordButton = screen.getByRole("button", { name: /Change password/i });
  expect(changePasswordButton).toBeEnabled();

  // AND WHEN
  await userEvent.click(changePasswordButton);

  // THEN
  expect(await screen.findByText("An unexpected error occurred.")).toBeInTheDocument();
});
