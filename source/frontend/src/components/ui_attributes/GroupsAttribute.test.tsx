// @ts-nocheck


/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render} from '@testing-library/react';
import React from "react";
import GroupsAttribute from "./GroupsAttribute";

afterEach(cleanup);

let props = {};
props.item = {}
let attribute = {name: 'myselection', type: 'groups', listValueAPI: '/admin/groups', description: 'testattribute'}

// Function stubs
const handleUserInput = () => {

}

const displayInfoLink = () => {

}

const setup = () => {
  const comp =  render(
    <GroupsAttribute
    attribute={attribute}
    isReadonly={false}
    value={undefined}
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

test('GroupsAttribute displays the label and text provided', () => {
  setup()
  expect(screen.getByText(attribute.description)).toBeTruthy();
});