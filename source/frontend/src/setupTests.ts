// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import "@testing-library/jest-dom";

import { Amplify } from "@aws-amplify/core";
import { setupServer } from "msw/node";
import { config } from "./__tests__/amplify_test_config";
import { mock_user_api } from "./__tests__/mocks/user_api";
import { mock_app_api } from "./__tests__/mocks/app_api";
import { mock_wave_api } from "./__tests__/mocks/wave_api";
import { mock_credentialmanager_api } from "./__tests__/mocks/credentialmanager_api";
import { mock_ssm_api } from "./__tests__/mocks/ssm_api";
import { mock_admin_api } from "./__tests__/mocks/admin_api";
import { mock_login_api } from "./__tests__/mocks/login_api";
import { mock_tools_api } from "./__tests__/mocks/tools_api";

jest.setTimeout(30000); // stop any test if running for more than 30 seconds

(window as any).env = {
  API_REGION: "us-east-1",
  API_USER: "random-s8o9g",
  API_ADMIN: "random-sx0c2",
  API_LOGIN: "random-b579",
  API_TOOLS: "random-n6l2",
  API_VPCE_ID: "",
  API_SSMSocket: "random-b804a",
  COGNITO_REGION: "us-east-1",
  COGNITO_USER_POOL_ID: "us-east-1_abcdefg",
  COGNITO_APP_CLIENT_ID: "abcdefg",
  COGNITO_HOSTED_UI_URL: "",
  VERSION_UI: "v4.0.0",
};

// Establish API mocking before all tests.
export const server = setupServer(
  // Define default mock responses for all endpoints. can be overwritten for individual tests.
  ...mock_admin_api,
  ...mock_login_api,
  ...mock_user_api,
  ...mock_app_api,
  ...mock_wave_api,
  ...mock_ssm_api,
  ...mock_credentialmanager_api,
  ...mock_tools_api
);
beforeAll(() => {
  server.listen();

  // provide all API names to Amplify but redirect all requests to mock server
  Amplify.configure(config);
});

beforeEach(() => {
  jest.resetAllMocks();
});

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests.
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished.
afterAll(() => server.close());

// mock export function of the external library XLSX to prevent create real files from test runs.
// for import/read functions, use actual implementation
jest.mock("xlsx", () => {
  const actualXlsx = jest.requireActual("xlsx");
  return {
    ...actualXlsx,
    writeFile: jest.fn(),
  };
});

jest.mock("ace-builds", () => {
  return {
    edit: jest.fn(),
  };
});

global.ResizeObserver = class ResizeObserver {
  observe() {}

  unobserve() {}

  disconnect() {}
};
