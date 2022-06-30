window.env = {
  API_REGION: "{{region}}",
  API_USER: "https://{{user-api}}.execute-api.{{region}}.amazonaws.com/prod",
  API_ADMIN: "https://{{admin-api}}.execute-api.{{region}}.amazonaws.com/prod",
  API_LOGIN: "https://{{login-api}}.execute-api.{{region}}.amazonaws.com/prod",
  API_TOOLS: "https://{{tools-api}}.execute-api.{{region}}.amazonaws.com/prod",
  API_SSMSocket: "wss://{{ssm-ws-api}}.execute-api.{{region}}.amazonaws.com/prod",
  COGNITO_REGION: "{{region}}",
  COGNITO_USER_POOL_ID: "{{user-pool-id}}",
  COGNITO_APP_CLIENT_ID: "{{app-client-id}}",
  VERSION_UI: "{{version}}"
};
