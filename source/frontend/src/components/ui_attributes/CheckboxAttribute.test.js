/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render, fireEvent} from '@testing-library/react';
import React from "react";
import CheckboxAttribute from "./CheckboxAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'test', type: 'tag', description: 'testattribute'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <CheckboxAttribute
    attribute={attribute}
    value={true}
    isReadonly={false}
    handleUserInput={handleUserInput}
    displayHelpInfoLink={displayInfoLink}
  />)

  const input = screen.getByLabelText(attribute.name)
  return {
    input,
    ...comp,
  }
}

test('CheckboxAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});

test('CheckboxAttribute trigger update', () => {
  const {input} = setup()
  fireEvent.click(input)
  expect(input.checked).toBe(false)
});