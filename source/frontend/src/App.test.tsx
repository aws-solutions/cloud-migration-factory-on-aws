import { TEST_SCHEMAS, TEST_SESSION_STATE } from "./__tests__/TestUtils";
import { render, screen, waitForElementToBeRemoved } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext } from "./contexts/SessionContext";
import React from "react";
import App from "./App";
import { server } from "./setupTests";
import { rest } from "msw";
import userEvent from "@testing-library/user-event";
import { Auth } from "@aws-amplify/auth";
import { NotificationContextProvider } from "./contexts/NotificationContext";
import { ToolsContextProvider } from "./contexts/ToolsContext";

function renderAppWithSession() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <NotificationContextProvider>
        <ToolsContextProvider>
          <SessionContext.Provider value={TEST_SESSION_STATE}>
            <div id="modal-root" />
            <App></App>
          </SessionContext.Provider>
        </ToolsContextProvider>
      </NotificationContextProvider>
    </MemoryRouter>
  );
}

test('it renders "loading" message until schema is loaded', async () => {
  // GIVEN
  server.use(
    rest.get("/admin/schema", (request, response, context) => {
      return response(context.status(500));
    })
  );

  // WHEN
  renderAppWithSession();

  // THEN
  const documentationMenu = screen.getByRole("button", { name: "Documentation" });
  expect(documentationMenu).toBeInTheDocument();
  expect(screen.getByText("Loading")).toBeInTheDocument();

  // WHEN
  await userEvent.click(documentationMenu);

  // THEN
  expect(screen.getByText("AWS Cloud Migration Factory Solution")).toBeInTheDocument();

  // AND WHEN
  await userEvent.click(screen.getByRole("button", { name: "" }));

  // THEN
  expect(screen.getByText("Change Password")).toBeInTheDocument();
  expect(screen.getByText("Sign out")).toBeInTheDocument();

  // AND WHEN
  jest.spyOn(Auth, "signOut").mockImplementation(jest.fn());
  await userEvent.click(screen.getByText("Sign out"));

  // THEN
  expect(Auth.signOut).toHaveBeenCalled();
});

test("it renders the dashboard after schema is loaded", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/schema", (request, response, context) => {
      return response(context.status(200), context.json(TEST_SCHEMAS));
    })
  );
  renderAppWithSession();

  // WHEN loading is finished
  await waitForElementToBeRemoved(screen.getByText("Loading"));

  // THEN
  expect(await screen.findByText(/migration factory overview/i)).toBeInTheDocument();
  expect(await screen.findByText(/overview of the status within the migration factory/i)).toBeInTheDocument();
});

test("it renders an error when schema load fails", async () => {
  // GIVEN
  server.use(
    rest.get("/admin/schema", (request, response, context) => {
      return response(context.status(403));
    })
  );
  renderAppWithSession();

  // WHEN loading is finished

  // THEN
  expect(await screen.findByText(/Error/i)).toBeInTheDocument();
  screen.logTestingPlaygroundURL();
  expect(await screen.findByText(/403/i)).toBeInTheDocument();
});
