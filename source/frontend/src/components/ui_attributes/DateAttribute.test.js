/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render, fireEvent} from '@testing-library/react';
import React from "react";
import DateAttribute from "./DateAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'test', type: 'date', description: 'testdateattribute'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <DateAttribute
    attribute={attribute}
    isReadonly={false}
    value={'2023/01/01'}
    errorText={null}
    handleUserInput={handleUserInput}
    displayHelpInfoLink={displayInfoLink}
  />)

  const input = screen.getByLabelText(attribute.name)
  return {
    input,
    ...comp,
  }
}

test('DateAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});

test('DateAttribute enter date to trigger update', () => {
  const {input} = setup()
  fireEvent.change(input, {target: {value: '2023/01/02'}})
  expect(input.value).toBe('2023/01/02')
});