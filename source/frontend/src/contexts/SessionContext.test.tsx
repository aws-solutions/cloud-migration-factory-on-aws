import {MemoryRouter} from "react-router-dom";
import React from "react";
import {render, screen} from "@testing-library/react";
import {SessionContextProvider} from "./SessionContext";
import {Auth} from "@aws-amplify/auth";

describe('before user is logged in', () => {

  function renderAppWithoutSession() {
    return render(
      <MemoryRouter initialEntries={['/']}>
        <SessionContextProvider>
          <div>App Placeholder</div>
        </SessionContextProvider>
      </MemoryRouter>
    );
  }

  test('it renders the login form instead of the App', async () => {
    // WHEN
    renderAppWithoutSession();

    // THEN
    expect(await screen.findByRole('heading', {name: /aws cloud migration factory/i})).toBeInTheDocument();
    expect(await screen.findByLabelText('Username')).toBeInTheDocument();
    expect(await screen.findByLabelText('Password')).toBeInTheDocument();

    // if not authenticated, the App that SessionContextProvider is wrapping should not be rendered
    expect(screen.queryByText('App Placeholder')).not.toBeInTheDocument();
  })

})

describe('when user is logged in', () => {

  function renderApp() {
    return render(
      <MemoryRouter initialEntries={['/']}>
        <SessionContextProvider>
          <div>App Placeholder</div>
        </SessionContextProvider>
      </MemoryRouter>
    );
  }

  test('it renders the the App', async () => {
    // GIVEN
    const getToken = {
      getJwtToken: () => `a.ewogICJzdWIiOiAiNDcyMzc1NTEtMzMxZS00NGE4LWEwMGItNjdjNzM5Y2U5Njc2IiwKICAiY29nbml0bzpncm91cHMiOiBbCiAgICAiYWRtaW4iCiAgXSwKICAiZW1haWxfdmVyaWZpZWQiOiB0cnVlLAogICJpc3MiOiAiaHR0cHM6Ly9jb2duaXRvLWlkcC51cy1lYXN0LTEuYW1hem9uYXdzLmNvbS91cy1lYXN0LTFfRFRqSWVGa1NQIiwKICAiY29nbml0bzp1c2VybmFtZSI6ICI0NzIzNzU1MS0zMzFlLTQ0YTgtYTAwYi02N2M3MzljZTk2NzYiLAogICJvcmlnaW5fanRpIjogImVjNjU3ZTc3LWZjNzYtNGNkMS05NWFiLTkxMGQzYzczYWU2MiIsCiAgImF1ZCI6ICIzMjhtcGc0MDVlMmc0ZWNxNXJyanNjN20zYSIsCiAgImV2ZW50X2lkIjogImE5YzY1MzlhLTFkOTItNDRlOS05OWM0LTNhMmMzNjhkMTZmYSIsCiAgInRva2VuX3VzZSI6ICJpZCIsCiAgImF1dGhfdGltZSI6IDE2OTYwMTk5MDUsCiAgImV4cCI6IDE2OTYwMjM1MDUsCiAgImlhdCI6IDE2OTYwMTk5MDUsCiAgImp0aSI6ICI5NjY2NmY1Yi04YjFiLTQzNTEtYTJjZC1lNzI0M2Y3ZDZhNmEiLAogICJlbWFpbCI6ICJmb29AZXhhbXBsZS5jb20iCn0=`
    };
    const session: any = {
      getIdToken: () => getToken,
      getAccessToken: () => getToken,
    };
    jest.spyOn(Auth, 'currentSession').mockImplementation(() => Promise.resolve(session));

    // WHEN
    renderApp();

    // THEN
    expect(await screen.findByText('App Placeholder')).toBeInTheDocument();
  })

})
