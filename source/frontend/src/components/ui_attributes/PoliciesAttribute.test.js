/**
 * @jest-environment jsdom
 */

/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render} from '@testing-library/react';
import React from "react";
import PoliciesAttribute from "./PoliciesAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'myselection', type: 'policies', listValueAPI: '/admin/groups', description: 'testattribute'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <PoliciesAttribute
    attribute={attribute}
    isReadonly={false}
    value={undefined}
    options={[{label: 'All', value: '__system_all'}, {label: 'testpolicy', value: '1'}]}
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

test('PoliciesAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});