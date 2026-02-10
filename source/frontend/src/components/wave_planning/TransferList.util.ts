/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Updates the relationship between parent and child records when children are either moved to a different parent or removed from their current parent.
 *
 * @param args - Configuration object containing all necessary parameters
 * @param args.action - Specifies whether to "move" children to another parent or "remove" them from current parent
 * @param args.parent - Parent entity configuration
 * @param args.parent.valueAttribute - Identifier attribute shared between parent and child entities
 * @param args.parent.multivalueRelationshipAttribute - Optional attribute in parent that stores array of child references
 * @param args.child - Child entity configuration
 * @param args.child.relationshipAttribute - Optional attribute in child that references parent
 * @param args.child.valueAttribute - Identifier attribute of child entity
 * @param args.children - Array of all child records
 * @param args.parents - Array of all parent records
 * @param args.targetParentId - ID of the target parent when moving children (required for "move" action)
 * @param args.selectedChildren - Array of child records to be moved or removed
 *
 * @returns Object containing:
 *          - updatedChildren: Array of child records with updated parent references
 *          - updatedParents: Array of parent records with updated child references (undefined if no parent updates needed)
 *
 * @typeParam P - Type of parent entity
 * @typeParam C - Type of child entity
 */
export function updateParentsChildren<P, C>(args: {
  readonly action: "move" | "remove";
  readonly parent: {
    readonly valueAttribute: keyof P;
    readonly multivalueRelationshipAttribute?: keyof P;
  };
  readonly child: {
    readonly relationshipAttribute?: keyof C;
    readonly valueAttribute: keyof C;
  };
  readonly children: C[];
  readonly parents: P[];
  readonly targetParentId?: string;
  readonly selectedChildren: C[];
}): { updatedParents: P[] | undefined; updatedChildren: C[] } {
  const { action, parent, child, parents, children, selectedChildren, targetParentId } = args;
  const childRelationshipAttribute = child.relationshipAttribute ?? parent.valueAttribute;
  const updatedChildren = children.map((item: C) =>
    selectedChildren.includes(item)
      ? {
          ...item,
          // If move action, update the child relationship attribute, otherwise it's remove so set to undefined
          [childRelationshipAttribute]: action === "move" ? targetParentId : undefined,
        }
      : item
  );

  let updatedParents = undefined;
  // Update parent multivalue-relationship attribute if related properties provided
  if (parent.multivalueRelationshipAttribute && child.valueAttribute) {
    // Assign to local variables so that TypeScript infer their type as string in the callback
    const parentRelationshipAttribute = parent.multivalueRelationshipAttribute;
    const childValueAttribute = child.valueAttribute;

    updatedParents = parents.map((item: P) => {
      const multiValueRelationship = item[parentRelationshipAttribute] ?? [];
      // Skip if somehow the multivalue-relationship attribute is not an array
      if (!Array.isArray(multiValueRelationship)) {
        console.warn(
          `The multivalue-relationship attribute ${String(parentRelationshipAttribute)} of ${item} is not an array`
        );
        return item;
      }
      const childrenIds = selectedChildren
        .map((c) => c[childValueAttribute])
        .filter((x) => x !== undefined && x !== null);
      const relationshipWithoutSelectedChildren = multiValueRelationship.filter((id) => !childrenIds.includes(id));
      // If the parent is the target parent, update the multivalue-relationship
      if (item[parent.valueAttribute] === targetParentId) {
        return {
          ...item,
          [parentRelationshipAttribute]:
            // If move action, add child id to the parent multivalue-relationship attribute array and deduplicate (in case)
            // Otherwise it's remove so remove from the array
            action === "move"
              ? Array.from(new Set([...multiValueRelationship, ...childrenIds]))
              : relationshipWithoutSelectedChildren,
        };
      } else {
        // Remove the selected children ids from the multivalue-relationship attribute array
        return {
          ...item,
          [parentRelationshipAttribute]: relationshipWithoutSelectedChildren,
        };
      }
    });
  }

  return { updatedChildren, updatedParents };
}
/**
 * Checks if any specified property value of an object contains a given search term (case-insensitive).
 *
 * @param item - Object to search within
 * @param filteringText - Search term to look for
 * @param filteringColumns - Optional array of property keys to search in. If not provided, searches all properties of the item
 * @returns `true` if any specified property value contains the search term, `false` otherwise
 */
export function valueContainsKeyword(
  item: Record<string, unknown>,
  filteringText: string,
  filteringColumns?: string[]
) {
  const searchTermLower = filteringText.toLowerCase();
  return (filteringColumns ?? Object.keys(item))
    .map((key) => (key in item ? item[key] : undefined))
    .some((value) => {
      if (value === null || value === undefined) return false;
      return String(value).toLowerCase().includes(searchTermLower);
    });
}
