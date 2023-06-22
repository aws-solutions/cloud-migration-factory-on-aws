/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render, fireEvent} from '@testing-library/react';
import React from "react";
import TagAttribute from "./TagAttribute";

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
    <TagAttribute
    attribute={attribute}
    tags={[{key: 'testkey', value: 'testvalue'}]}
    handleUserInput={handleUserInput}
    displayHelpInfoLink={displayInfoLink}
  />)

  const input = screen.getByPlaceholderText('Enter key')
  return {
    input,
    ...comp,
  }
}

test('TagAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});

test('TagAttribute trigger update', () => {
  const {input} = setup()
  fireEvent.change(input, {target: {value: 'new key'}})
  expect(input.value).toBe('new key')
});