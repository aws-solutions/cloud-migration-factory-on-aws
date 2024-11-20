/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import * as main from "./main";

const resultObject = { existingkey: "existing_value", newkey: "neyvalue" };
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
  const oldObject = { name: "thisone", existingkey: "existing_value", newkey: "newvalue" };
  const newObject = [{ name: "thisone", existingkey: "existing_value" }];
  expect(main.getChanges(oldObject, newObject, "name")).toEqual({ newkey: "newvalue" });
});

// Unit test for getNestedValuePath in main.js
test("Returns the value of a nested object based on a path.", () => {
  const nestedObject = { name: "thisone", existingkey: "existing_value", newkey: "newvalue" };
  expect(main.getNestedValuePath(nestedObject, "existingkey")).toBe("existing_value");
});

//Unit test for getNestedValue of main.js
test("Returns the value of a nested object based on a path.", () => {
  const nestedObject = { name: "thisone", existingkey: "existing_value", newkey: "newvalue" };
  expect(main.getNestedValue(nestedObject, "existingkey")).toBe("existing_value");
});

//Unit test for setNestedValuePath of main.js
test("Sets the value of a nested object based on a path.", () => {
  const nestedObject = { name: "thisone", nested: { existingkey: "existing_value", newkey: "newvalue" } };
  main.setNestedValuePath(nestedObject, "nested.existingkey", "newvalue");
  expect(nestedObject).toEqual({ name: "thisone", nested: { existingkey: "newvalue", newkey: "newvalue" } });
});

//Unit test for sortAscendingComparator of main.js
test("Compare a and b in ascending order based on a key.", () => {
  let result = main.sortAscendingComparator("a", "a");
  expect(result).toEqual(0);
  result = main.sortAscendingComparator("a", "b");
  expect(result).toEqual(-1);
  result = main.sortAscendingComparator("b", "a");
  expect(result).toEqual(1);

  result = main.sortAscendingComparator(5, 5);
  expect(result).toEqual(0);
  result = main.sortAscendingComparator(5, 6);
  expect(result).toEqual(-1);
  result = main.sortAscendingComparator(5, 4);
  expect(result).toEqual(1);

  result = main.sortAscendingComparator(true, true);
  expect(result).toEqual(0);
  result = main.sortAscendingComparator(true, false);
  expect(result).toEqual(1);
  result = main.sortAscendingComparator(false, true);
  expect(result).toEqual(-1);

  const dd = new Date();
  const dd2 = new Date(dd.getTime() + 1000);
  result = main.sortAscendingComparator(dd, dd);
  expect(result).toEqual(0);
  result = main.sortAscendingComparator(dd2, dd);
  expect(result).toEqual(1);
  result = main.sortAscendingComparator(dd, dd2);
  expect(result).toEqual(-1);
});

test("deepEquals for different scenrios", () => {
  expect(main.deepEqual({ member1: "A" }, { member1: "A" })).toEqual(true);
  expect(main.deepEqual({ member1: "A" }, { member1: "A", member2: "B" })).toEqual(false);
  expect(main.deepEqual({ member1: "A" }, { member1: "B" })).toEqual(false);
  expect(main.deepEqual({ member1: "A" }, { member1111: "A" })).toEqual(false);

  expect(main.deepEqual(null, null)).toEqual(true);
  expect(main.deepEqual(undefined, undefined)).toEqual(true);

  expect(main.deepEqual({}, null)).toEqual(false);
  expect(main.deepEqual({}, undefined)).toEqual(false);
});

test("validateTags function for correct required tag keys", () => {
  let attribute = {
    type: 'tag,',
    requiredTags: [
      { key: "key", value: "" }
    ]
  }

  expect(main.validateTags(attribute, [{ key: "key", value: "value"}, { key: "key1", value: "value1"}])).toBeNull();
});

test("validateTags function for missing required tag key", () => {
  let attribute = {
    type: 'tag,',
    requiredTags: [
      { key: "key", value: "value" },
      { key: "key2", value: "value2" }
    ]
  }

  expect(main.validateTags(attribute, [{ key: "key", value: "value"}])).toEqual(["key2 - tag required."]);
});

test("validateTags function for required tag invalid value", () => {
  let attribute = {
    type: 'tag,',
    requiredTags: [
      { key: "key", value: "^no$" }
    ]
  }

  expect(main.validateTags(attribute, [{ key: "key", value: "value"}])).toEqual(["key - Value does not meet custom validation (RegEx : ^no$), please update."]);
});

test("validateTags function for required tag invalid key/value based on default regex", () => {
  let attribute = {
    type: 'tag,',
    requiredTags: [
      { key: "key", value: "" }
    ],
    validation_regex: "^yes$"
  }

  expect(main.validateTags(attribute, [{ key: "key", value: "value"}])).toEqual(["key - Value does not meet custom validation (RegEx : ^yes$), please update."]);
});

test("validateTags function for tag key too long", () => {
  let attribute = {
    type: 'tag,',
  }

  expect(main.validateTags(attribute, [{ key: "a".repeat(129), value: "value"}])).toEqual(["a".repeat(129) + " - maximum Key characters is 128, currently 129"]);
});

test("validateTags function for tag value too long", () => {
  let attribute = {
    type: 'tag,',
  }

  expect(main.validateTags(attribute, [{ key: "a", value: "a".repeat(257)}])).toEqual(["a".repeat(257) + " - maximum Value characters is 256, currently 257"]);
});