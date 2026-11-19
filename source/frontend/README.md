This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

To install the project, you can run:

### `npm install`

To run the project, you can run:

### `npm start`

Runs the app in the development mode.<br>
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.<br>
You will also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.<br>
See the section about [running tests](#running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.<br>
It correctly bundles React in production mode and optimizes the build for the best performance.

### `npm run generate`

The project uses a code generator (`bin/generate-validators.ts`) to create standalone validation functions for JSON schemas.
The generated code is output to the `vendors/validators.mjs` and committed into git repo.

Refer to [Validation Function Generation](#validation-function-generation) for details.

### `npm run storybook`

Launches Storybook in development mode.<br>
Open [http://localhost:6006](http://localhost:6006) to view it in the browser.

### `npm run build-storybook`

Builds the Storybook as a static web application.<br>
The build output will be placed in the `storybook-static` folder.<br>
This can be deployed to any static hosting service for sharing with your team.

## Storybook

This project uses [Storybook](https://storybook.js.org/) for component development and documentation. Storybook is a frontend workshop for building UI components and pages in isolation. It makes development faster and easier by isolating components.

### Why Storybook?

Storybook provides several benefits to our development workflow:

- 📝 **Component Documentation**: Automatically generates documentation for components
- 🔍 **Development in Isolation**: Build and test components independently
- 🧪 **Testing**: Makes it easier to test different component states and edge cases
- 🎨 **Design System**: Helps maintain consistency across components
- 👥 **Team Collaboration**: Improves communication between developers, designers, and stakeholders
- ⚡ **Faster Development**: Speeds up component development with instant feedback
- 🔄 **Interactive Development**: Test components with different props and screen sizes in real-time

### Creating Stories

We encourage developers to create stories for new components. To add a story:

1. Create a new file named `[ComponentName].stories.tsx` in the same directory as your component
2. Use this basic template:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { YourComponent } from "./YourComponent";

const meta: Meta<typeof YourComponent> = {
  title: "YourComponent",
  component: YourComponent,
};

export default meta;
type Story = StoryObj<typeof YourComponent>;

export const Default: Story = {
  args: {
    // Add your component's props here
  },
};
```

## Validation Function Generation

The project uses [Ajv](https://www.npmjs.com/package/ajv) for JSON schema validation, but it does not work with production `index.html`. This is because the CSP does not allow dynamic code evaluation that
Ajv is using by default.

Fortunately Ajv provides [Standalone validation code](https://ajv.js.org/standalone.html) to solve
this problem. The benefits are:

- Reduced bundle size
- Avoiding dynamic code evaluation

### When to run `npm run generate`
The `generate` script is automatically run during the build process (`npm run build`). However, you should manually run `npm run generate` when you change `bin/generate-validators.ts`.