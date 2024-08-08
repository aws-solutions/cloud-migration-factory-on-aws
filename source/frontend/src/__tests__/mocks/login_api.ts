import { rest } from "msw";

export const mock_login_api = [
  rest.get("/login/groups", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];
