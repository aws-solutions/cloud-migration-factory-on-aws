import { rest } from "msw";

export const mock_app_api = [
  rest.get("/user/app", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];
