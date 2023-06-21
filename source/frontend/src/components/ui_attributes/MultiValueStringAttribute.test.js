/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render, fireEvent} from '@testing-library/react';
import React from "react";
import MultiValueStringAttribute from "./MultiValueStringAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attributeValue = undefined;
let attribute = {name: 'testattribute', type: 'multivalue-string', description: 'testattribute'}
let attributeNoDesc = {name: 'testattribute', type: 'multivalue-string'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <MultiValueStringAttribute
    attribute={attribute}
    isReadonly={false}
    value={attributeValue}
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

const setupDesc = () => {
  const comp =  render(
    <MultiValueStringAttribute
      attribute={attributeNoDesc}
      isReadonly={false}
      value={attributeValue}
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

test('MultiValueStringAttribute displays the label provided.', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});

test('MultiValueStringAttribute enter string to update', () => {
  const {input} = setup()
  fireEvent.change(input, {target: {value: 'newvalue'}})
  expect(input.value).toBe('newvalue')
});

test('MultiValueStringAttribute clear value', () => {
  const {input} = setup()
  fireEvent.change(input, {target: {value: ''}})
  expect(input.value).toBe('')
});

test('MultiValueStringAttribute displays the label provided as name.', () => {
  setupDesc()
  expect(screen.getByText(attribute.name)).toBeTruthy();
});