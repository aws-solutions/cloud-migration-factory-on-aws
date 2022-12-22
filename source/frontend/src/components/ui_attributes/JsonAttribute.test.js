/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// JsonAttribute.test.js
import {cleanup, screen, render} from '@testing-library/react';
import JsonAttribute from "./JsonAttribute";
import {getNestedValuePath} from "../../resources/main";
import React from "react";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'test', type: 'json', description: 'testjsonattribute'}

test('TextAttribute displays the label and text provided', () => {
  const {} = render(
    <JsonAttribute
      key={'jsonattribute'}
      attribute={attribute}
      item={getNestedValuePath(props.item, attribute.name)}
      handleUserInput={props.handleUserInput}
      errorText={'validationError'}
    />
  );

  expect(screen.getByText(attribute.description)).toBeTruthy();

});