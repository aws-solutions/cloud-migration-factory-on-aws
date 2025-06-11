/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// Keeps track of how many items are selected
export function headerCounter(selectedItems: readonly any[], items: readonly any[]) {
  return selectedItems.length ? `(${selectedItems.length} of ${items.length})` : `(${items.length})`;
}

export function filterCounter(count: number | undefined) {
  return `${count} ${count === 1 ? "match" : "matches"}`;
}
