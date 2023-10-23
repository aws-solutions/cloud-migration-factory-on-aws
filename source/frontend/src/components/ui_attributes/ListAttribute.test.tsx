// @ts-nocheck


/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render} from '@testing-library/react';
import React from "react";
import ListAttribute from "./ListAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'myselection', type: 'list', listvalue: '1,2,3,4,5', description: 'testattribute'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <ListAttribute
    attribute={attribute}
    isReadonly={false}
    value={'1'}
    errorText={null}
    handleUserInput={handleUserInput}
    displayHelpInfoLink={displayInfoLink}
  />)

  const input = screen.getAllByLabelText(attribute.name)
  return {
    input,
    ...comp,
  }
}

test('ListAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});

// test('ListAttribute select value to trigger update', () => {
//   const {input} = setup()
//   console.debug(input);
//   fireEvent.click(input, {target: {value: '2'}})
//   expect(input.value).toBe('2')
// });