import { Alert } from "@cloudscape-design/components";
import { Application, Database, MoveGroup, Server, WPMJobStep } from "../../models";
import { tryParseFloat } from "../../resources/main";

// Create a mapping object for index to enum
const stepIndexToEnum: Readonly<Map<number, WPMJobStep>> = new Map([
  [0, "JOB_DETAILS"],
  [1, "MANAGE_APPLICATIONS"],
  [2, "MANAGE_MOVE_GROUPS"],
  [3, "MANAGE_WAVES"],
]);

export function indexToStep(index: number): WPMJobStep {
  const step = stepIndexToEnum.get(index);
  if (!step) {
    throw new Error(`Invalid index: ${index}`);
  }
  return step;
}

export function stepToIndex(step: WPMJobStep): number {
  for (const [index, value] of stepIndexToEnum) {
    if (value === step) return index;
  }
  throw new Error(`Invalid step: ${step}`);
}

/**
 * Updates a move group to include all server IDs and database IDs from the provided lists,
 * ensures app IDs from servers and databases are included, and updates applications to include the move group ID
 *
 * @param moveGroup - The move group to update
 * @param servers - Array of servers to include in the move group
 * @param databases - Array of databases to include in the move group
 * @param applications - Array of all applications to update with the move group ID
 * @returns Updated move group with synchronized server_ids, database_ids, and app_ids
 */
export function syncAssetRelationships(
  moveGroup: MoveGroup,
  servers: Server[],
  databases: Database[],
  applications: Application[]
): {
  updatedMoveGroup: MoveGroup;
  updatedApplications: Application[];
} {
  if (!moveGroup) {
    return {
      updatedMoveGroup: moveGroup,
      updatedApplications: applications,
    };
  }

  // Create a new move group object to avoid mutating the original
  const updatedMoveGroup: MoveGroup = {
    ...moveGroup,
    // Preserve existing arrays if they exist
    server_ids: [...(moveGroup.server_ids || [])],
    database_ids: [...(moveGroup.database_ids || [])],
    app_ids: [...(moveGroup.app_ids || [])],
  };

  // Filter servers and databases that belong to this move group
  const moveGroupServers = servers.filter((server) => server.move_group_id === moveGroup.move_group_id);
  const moveGroupDatabases = databases.filter((database) => database.move_group_id === moveGroup.move_group_id);

  // set move group id to null for servers and databases that dont have move group id associated

  // Extract server IDs / Database IDs from filtered Asets
  const serverIds = moveGroupServers.map((server) => server.server_id);
  const databaseIds = moveGroupDatabases.map((database) => database.database_id);

  // MG --> Server/Database
  updatedMoveGroup.server_ids = serverIds;
  updatedMoveGroup.database_ids = databaseIds;

  // Collect all app IDs from servers and databases
  const appIdsSet = new Set<string>();

  // Add app IDs from servers and databases
  moveGroupServers.forEach((server) => {
    if (server.app_ids && Array.isArray(server.app_ids)) {
      server.app_ids.forEach((appId) => appIdsSet.add(appId));
    }
  });

  moveGroupDatabases.forEach((database) => {
    if (database.app_ids && Array.isArray(database.app_ids)) {
      database.app_ids.forEach((appId) => appIdsSet.add(appId));
    }
  });

  // Convert Set to Array for app IDs
  const appIds = Array.from(appIdsSet);

  // Merge new app IDs  MG --> APP
  updatedMoveGroup.app_ids = appIds;

  // Update counts for reporting
  updatedMoveGroup.server_count = updatedMoveGroup.server_ids.length;

  // Update total storage size for group
  updatedMoveGroup.total_server_storage = moveGroupServers.reduce(
    (acc, server) => acc + tryParseFloat(server.storage_size, 0),
    0
  );

  // Create a new applications array only if changes are needed
  const updatedApplications = [...applications];
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let hasChanges = false;

  // Create a Set of app IDs for faster lookups
  const appIdsInMoveGroup = new Set(appIds);

  // Update applications - add or remove move group ID as needed
  applications.forEach((app, index) => {
    if (!app.app_id) return;

    const moveGroupIds = app.move_group_ids || [];
    const hasMoveGroupId = moveGroupIds.includes(moveGroup.move_group_id);
    const shouldHaveMoveGroupId = appIdsInMoveGroup.has(app.app_id);

    // Case 1: App should have move group ID but doesn't - add it
    if (shouldHaveMoveGroupId && !hasMoveGroupId) {
      hasChanges = true;
      updatedApplications[index] = {
        ...app,
        move_group_ids: [...moveGroupIds, moveGroup.move_group_id],
      };
    }
    // Case 2: App shouldn't have move group ID but does - remove it
    else if (!shouldHaveMoveGroupId && hasMoveGroupId) {
      hasChanges = true;
      updatedApplications[index] = {
        ...app,
        move_group_ids: moveGroupIds.filter((id) => id !== moveGroup.move_group_id),
      };
    }
    // Case 3: No change needed
  });

  return {
    updatedMoveGroup,
    updatedApplications,
  };
}

// Alert message for Readonly steps
export const ReadOnlyAlert = () => (
  <Alert type="warning">
    This step is completed and view-only. If you would like to make changes, please cancel this job and create a new job
    instead.
  </Alert>
);
