import {rest} from "msw";

export const mock_wave_api = [
  rest.get('/user/wave', (request, response, context) => {
    return response(
      context.status(200),
      context.json([])
    );
  }),
]