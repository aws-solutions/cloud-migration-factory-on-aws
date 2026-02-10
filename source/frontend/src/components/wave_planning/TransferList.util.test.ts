/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { sampleWaves, sampleMoveGroups } from "../../../test_data";
import { MoveGroup, Wave } from "../../models";
import { updateParentsChildren } from "./TransferList.util";

describe("updateParentsChildren", () => {
  const sourceParentId = "wave-1";
  const targetParentId = "wave-2";

  it("should move selected children to target parent", () => {
    const parents = sampleWaves();
    const children = sampleMoveGroups();
    const selectedChildren = children.filter((mg) => mg.wave_id === sourceParentId);
    const { updatedParents, updatedChildren } = updateParentsChildren<Wave, MoveGroup>({
      action: "move",
      parent: {
        valueAttribute: "wave_id",
        multivalueRelationshipAttribute: "move_group_ids",
      },
      child: {
        valueAttribute: "move_group_id",
      },
      children,
      parents,
      selectedChildren,
      targetParentId,
    });

    for (const [i, p] of updatedParents?.entries() ?? []) {
      if (p.wave_id === sourceParentId) {
        expect(p).toEqual({ ...parents[i], move_group_ids: [] });
      } else if (p.wave_id === targetParentId) {
        expect(p).toEqual({
          ...parents[i],
          move_group_ids: [...(parents[i].move_group_ids ?? []), ...selectedChildren.map((mg) => mg.move_group_id)],
        });
      } else {
        expect(p).toEqual(parents[i]);
      }
    }

    for (const [i, c] of updatedChildren.entries() ?? []) {
      if (c.wave_id === targetParentId) {
        expect(c).toEqual({ ...children[i], wave_id: targetParentId });
      } else {
        expect(c).toEqual(children[i]);
      }
    }
  });

  it("should work in the same way as remove if targetParentId is undefined", () => {
    const parents = sampleWaves();
    const children = sampleMoveGroups();
    const selectedChildren = children.filter((mg) => mg.wave_id === sourceParentId);
    const { updatedParents, updatedChildren } = updateParentsChildren<Wave, MoveGroup>({
      action: "move",
      parent: {
        valueAttribute: "wave_id",
        multivalueRelationshipAttribute: "move_group_ids",
      },
      child: {
        valueAttribute: "move_group_id",
      },
      children,
      parents,
      selectedChildren,
      targetParentId: undefined,
    });

    for (const [i, p] of updatedParents?.entries() ?? []) {
      if (p.wave_id === sourceParentId) {
        expect(p).toEqual({ ...parents[i], move_group_ids: [] });
      } else {
        expect(p).toEqual(parents[i]);
      }
    }

    for (const [i, c] of updatedChildren.entries() ?? []) {
      const selectedChildrenIds = selectedChildren.map((c) => c.move_group_id);
      if (selectedChildrenIds.includes(c.move_group_id)) {
        expect(c).toEqual({ ...children[i], wave_id: undefined });
      } else {
        expect(c).toEqual(children[i]);
      }
    }
  });

  it("should remove selected children from source parent", () => {
    const parents = sampleWaves();
    const children = sampleMoveGroups();
    const selectedChildren = children.filter((mg) => mg.wave_id === sourceParentId);
    const { updatedParents, updatedChildren } = updateParentsChildren<Wave, MoveGroup>({
      action: "remove",
      parent: {
        valueAttribute: "wave_id",
        multivalueRelationshipAttribute: "move_group_ids",
      },
      child: {
        valueAttribute: "move_group_id",
      },
      children,
      parents,
      selectedChildren,
    });

    for (const [i, p] of updatedParents?.entries() ?? []) {
      if (p.wave_id === sourceParentId) {
        expect(p).toEqual({ ...parents[i], move_group_ids: [] });
      } else {
        expect(p).toEqual(parents[i]);
      }
    }

    for (const [i, c] of updatedChildren.entries() ?? []) {
      const selectedChildrenIds = selectedChildren.map((c) => c.move_group_id);
      if (selectedChildrenIds.includes(c.move_group_id)) {
        expect(c).toEqual({ ...children[i], wave_id: undefined });
      } else {
        expect(c).toEqual(children[i]);
      }
    }
  });
});
