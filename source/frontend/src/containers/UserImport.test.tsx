// @ts-nocheck


/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {cleanup, screen, render, fireEvent, waitFor} from '@testing-library/react';
import React from "react";
import UserImport from "./UserImport";
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom'
const {promises: fsPromises} = require('fs');
afterEach(cleanup);

let props = {};
props.item = {}
var item = {
  "script": {
    "package_uuid": "d5ec74d4-9410-4525-83ce-c162ba36ed69"
  }
}
const testFilePath = './test_data/'
const validCSVFilename = 'test_valid.csv'
const invalidCSVFilename = 'test_invalid.csv'
const validExcelFilename = 'test_valid.xlsx'
const invalidExcelFilename = 'test_invalid.xlsx'
const mainSchemaFilename = 'default_schema.json'


const schemas = require('../../test_data/' + mainSchemaFilename)

// Function stubs
const handleUserInput = ev => {
  let valueArray = [];

  //Convert non-Array values to array in order to keep procedure simple.
  if(Array.isArray(ev)){
    valueArray = ev;
  } else {
    valueArray.push(ev);
  }

  for (const valueItem of valueArray) {
    setNestedValuePath(item, valueItem.field, valueItem.value);
  }
}

const handleStub = () => {

}

const setup = () => {
  const comp =  render(
    <UserImport
      schema={schemas}
    />)
  const input  = comp.container.querySelector(`input[name="file"]`);
  return {
    ...comp,
    input
  }
}

jest.mock("../actions/ServersHook", () => {
  return {
    useGetServers: () => {
      return [{
        isLoading: false,
        data: [],
        error: null
      }, {update: jest.fn()}];
    },
  };
});

jest.mock("../actions/ApplicationsHook", () => {
  return {
    useMFApps: () => {
      return [{
        isLoading: false,
        data: [],
        error: null
      }, {update: jest.fn()}];
    },
  };
});

jest.mock("../actions/WavesHook", () => {
  return {
    useMFWaves: () => {
      return [{
        isLoading: false,
        data: [],
        error: null
      }, {update: jest.fn()}];
    },
  };
});

jest.mock("../actions/DatabasesHook", () => {
  return {
    useGetDatabases: () => {
      return [{
        isLoading: false,
        data: [],
        error: null
      }, {update: jest.fn()}];
    },
  };
});

jest.mock("../actions/CredentialManagerHook", () => {
  return {
    useCredentialManager: () => {
      return [{
        isLoading: false,
        data: [],
        error: null
      }, {updateSecrets: jest.fn()}];
    },
  };
});

test('UserImport displays a main message title', () => {
  setup()
  expect(screen.getByText('Intake forms should be in CSV/UTF8 or Excel/xlsx format.')).toBeTruthy();
});

test('Upload valid csv file', async () => {
  const {input} = setup()
  const validFileContents = await fsPromises.readFile(testFilePath + validCSVFilename, 'utf-8');
  const file = new File([validFileContents], validCSVFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

  await waitFor(() => {
    userEvent.upload(input, file);
  });
  await new Promise((r) => setTimeout(r, 2000));
  expect(screen.getByText(validCSVFilename)).toBeTruthy();
});

test('Upload invalid csv file', async () => {
  const {input} = setup()
  const invalidFileContents = await fsPromises.readFile(testFilePath + invalidCSVFilename, 'utf-8');
  const file = new File([invalidFileContents], invalidCSVFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

  await waitFor(() => {
    userEvent.upload(input, file);
  });
  await new Promise((r) => setTimeout(r, 2000));
  expect(screen.getByText(invalidCSVFilename)).toBeTruthy();
});

test('Upload valid csv file and review upload', async () => {
  const {input} = setup()
  const validFileContents = await fsPromises.readFile(testFilePath + validCSVFilename, 'utf-8');
  const file = new File([validFileContents], validCSVFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

  await waitFor(() => {
    userEvent.upload(input, file);
  });

  await new Promise((r) => setTimeout(r, 2000));
  const nextButton = screen.getByText('Next')

  fireEvent.click(nextButton)
  await new Promise((r) => setTimeout(r, 2000));

  expect(screen.getByText('Your intake form has 2 informational validation messages.')).toBeTruthy();
});

test('Upload valid csv file and view commit overview', async () => {
  const comp = setup()
  const validFileContents = await fsPromises.readFile(testFilePath + validCSVFilename, 'utf-8');
  const file = new File([validFileContents], validCSVFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

  await waitFor(() => {
    userEvent.upload(comp.input, file);
  });
  await new Promise((r) => setTimeout(r, 2000));

  const nextButton = await screen.getByText('Next')
  expect(nextButton).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(nextButton)
  });

  const preUploadText = await screen.getByText('Pre-upload validation');
  expect(preUploadText).toBeInTheDocument();

  const nextButton1 = await screen.getByText('Next')
  expect(nextButton1).toBeInTheDocument();
  await waitFor(() => {
    fireEvent.click(nextButton1)
  });

  const uploadText = await screen.getByText('Upload Overview');
  expect(uploadText).toBeInTheDocument();

  expect(screen.getByText('unittest1')).toBeTruthy();
});

test('Upload valid Excel file', async () => {
  const {input} = setup()
  const validFileContents = await fsPromises.readFile(testFilePath + validExcelFilename);
  const file = new File([validFileContents], validExcelFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });

  await waitFor(() => {
    userEvent.upload(input, file);
  });
  await new Promise((r) => setTimeout(r, 2000));
  expect(screen.getByText(validExcelFilename)).toBeTruthy();
});

// test('Upload invalid Excel file', async () => {
//   const {input} = setup()
//   const invalidFileContents = await fsPromises.readFile(testFilePath + invalidExcelFilename);
//   const file = new File([invalidFileContents], invalidExcelFilename, { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
//   await waitFor(() => {
//     userEvent.upload(input, file);
//   });
//   await new Promise((r) => setTimeout(r, 2000));
//   expect(screen.getByText(invalidExcelFilename)).toBeTruthy();
// });