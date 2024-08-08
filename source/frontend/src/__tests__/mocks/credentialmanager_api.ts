import { rest } from "msw";

export const mock_credentialmanager_api = [
  rest.get("/credentialmanager", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];

export function generateTestCredentials(count: number): Array<any> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    ARN: "arn:aws:secretsmanager:us-east-1:111122223333:secret:dhdfh-1v6ypd",
    Name: "dhdfh",
    Description: "Secret for Migration Factory",
    LastChangedDate: "2023-09-27 18:09:37.946000+00:00",
    Tags: [
      {
        Key: "CMFUse",
        Value: "CMF Automation Credential Manager",
      },
    ],
    SecretVersionsToStages: {
      "4de1c130-d5d5-42f1-93c6-0642cc31aa17": ["AWSCURRENT"],
    },
    CreatedDate: "2023-09-27 18:09:37.908000+00:00",
    data: {
      USERNAME: "hdthhdh",
      PASSWORD: "*********",
      SECRET_TYPE: "OS",
      OS_TYPE: "Linux",
      IS_SSH_KEY: false,
    },
  }));
}
