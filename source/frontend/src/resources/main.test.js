/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

const main = require("./main");

const resultObject = {existingkey:'existing_value', newkey: 'neyvalue'};
// test("Returns JSON Object with all keys from both old and new JSON objects.", () => {
// const oldObject = {existingkey:'existing_value'};
//   const newObject = {existingkey:'existing_value', newkey: 'newvalue'};
//   const mergedObject = main.mergeKeys(oldObject,newObject);
//   console.log(mergedObject);
//   expect(mergedObject).toEqual({existingkey:'existing_value', newkey: 'newvalue'});
// });

test("Capitalize the first letter of the string argument.", () => {
  expect(main.capitalize("lowercase")).toBe("Lowercase");
});

test("Returns true if key exists in the object.", () => {
  expect(main.propExists(resultObject, "existingkey")).toBe(true);
});


test("Returns the differences between 2 objects based on a deep equals.", () => {
  const oldObject = {name: 'thisone', existingkey:'existing_value', newkey: 'newvalue'};
  const newObject = [{name: 'thisone', existingkey:'existing_value'}];
  expect(main.getChanges(oldObject, newObject, 'name' )).toEqual({newkey: 'newvalue'});
});

// Unit test for getNestedValuePath in main.js
test("Returns the value of a nested object based on a path.", () => {
  const nestedObject = {name: 'thisone', existingkey:'existing_value', newkey: 'newvalue'};
  expect(main.getNestedValuePath(nestedObject, "existingkey")).toBe("existing_value");
});

//Unit test for getNestedValue of main.js
test("Returns the value of a nested object based on a path.", () => {
  const nestedObject = {name: 'thisone', existingkey:'existing_value', newkey: 'newvalue'};
  expect(main.getNestedValue(nestedObject, "existingkey")).toBe("existing_value");
});

//Unit test for setNestedValuePath of main.js
test("Sets the value of a nested object based on a path.", () => {
  const nestedObject = {name: 'thisone', nested: {existingkey:'existing_value', newkey: 'newvalue'}};
  main.setNestedValuePath(nestedObject, "nested.existingkey", "newvalue");
  expect(nestedObject).toEqual({name: 'thisone', nested: {existingkey:'newvalue', newkey: 'newvalue'}});
});

//Unit test for sortAscendingComparator of main.js
test("Compare a and b in ascending order based on a key.", () => {
  const result = main.sortAscendingComparator("b", "a");
  expect(result).toEqual(1);
});