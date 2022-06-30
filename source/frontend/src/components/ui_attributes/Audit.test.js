/**
 * @jest-environment jsdom
 */

// Audit.test.js
import {cleanup, screen, render} from '@testing-library/react';
import Audit from "./Audit";
import React from "react";

afterEach(cleanup);

test('Audit displays all valid creations and modified information provided', () => {

  const props = {
    item: {
      "_history": {
        "createdBy": {
          "email": "test@test.com"
        },
        "createdTimestamp": '2022-01-01T01:01:01.0000000',
        "lastModifiedBy": {
          "email": "test1@test1.com"
        },
        "lastModifiedTimestamp": '2023-01-01T01:01:01.0000000'
      }
    }
  }

  const {queryByLabelText, getByLabelText} = render(
    <Audit item={props.item}/>
  );

  expect(screen.getByText(props.item._history.createdBy.email)).toBeTruthy();
  expect(screen.getByText('Created by')).toBeTruthy();
  expect(screen.getByText('Created on')).toBeTruthy();

  expect(screen.getByText(props.item._history.lastModifiedBy.email)).toBeTruthy();
  expect(screen.getByText('Last modified by')).toBeTruthy();
  expect(screen.getByText('Last updated on')).toBeTruthy();

});

test('Audit displays labels for items with no audit data.', () => {
  const props = {item: {}};
  const {} = render(
    <Audit item={props.item}/>
  );

  expect(screen.getByText('Created by')).toBeTruthy();
  expect(screen.getByText('Created on')).toBeTruthy();
  expect(screen.getByText('Last modified by')).toBeTruthy();
  expect(screen.getByText('Last updated on')).toBeTruthy();


});

test('Audit displays labels for items with no audit data but has _history.', () => {
  const props = {
    item: {
      "_history": {
      }
    }
  }
  const {} = render(
    <Audit item={props.item}/>
  );

  expect(screen.getByText('Created by')).toBeTruthy();
  expect(screen.getByText('Created on')).toBeTruthy();
  expect(screen.getByText('Last modified by')).toBeTruthy();
  expect(screen.getByText('Last updated on')).toBeTruthy();


});

test('Audit displays labels for items with no createdBy or lastModifiedBY email audit data.', () => {
  const props = {
    item: {
      "_history": {
        "createdBy": {
        },
        "createdTimestamp": '2022-01-01T01:01:01.0000000',
        "lastModifiedBy": {
        },
        "lastModifiedTimestamp": '2023-01-01T01:01:01.0000000'
      }
    }
  }
  const {} = render(
    <Audit item={props.item}/>
  );

  expect(screen.getByText('Created by')).toBeTruthy();
  expect(screen.getByText('Created on')).toBeTruthy();
  expect(screen.getByText('Last modified by')).toBeTruthy();
  expect(screen.getByText('Last updated on')).toBeTruthy();

});

