/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// FlashMessage.test.js
import {cleanup, screen, render} from '@testing-library/react';
import FlashMessage from "./FlashMessage";

afterEach(cleanup);

test('FlashMessage Displays current notifications', () => {
  const {} = render(
    <FlashMessage
      notifications={[{
        type: 'error',
        dismissible: true,
        header: "Test Message1",
        content: "Test message content 1"
      }]}
    />,
  );

  expect(screen.getByText('Test Message1')).toBeTruthy();
  expect(screen.getByText('Test message content 1')).toBeTruthy();

});