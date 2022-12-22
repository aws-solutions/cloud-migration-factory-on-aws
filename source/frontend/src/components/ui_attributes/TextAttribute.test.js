/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// TestAttribute.test.js
import {cleanup, screen, render} from '@testing-library/react';
import TextAttribute from "./TextAttribute";

afterEach(cleanup);

let labelName = 'TestAttributeLabel'
let childText = 'TestTextValue'


test('TextAttribute displays the label and text provided', () => {
  const {} = render(
    <TextAttribute
      key={'test-attribute'}
      label={labelName}
      loadingText={undefined}
      loading={false}
      children={childText}
    />,
  );

  expect(screen.getByText(labelName)).toBeTruthy();
  expect(screen.getByText(childText)).toBeTruthy();

});