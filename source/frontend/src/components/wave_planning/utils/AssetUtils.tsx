/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { Server, Database } from "../../../models";

/**
 * Interface representing an asset (server or database)
 */
export interface Asset {
  assetId: string;
  assetName: string;
  assetType: "server" | "database";
  app_ids: string[];
  move_group_id?: string;
  wpm_job_id?: string;
  [key: string]: string | string[] | number | boolean | undefined;
}

/**
 * Helper function to convert servers and databases to assets format
 * @param servers - Array of servers to convert
 * @param databases - Array of databases to convert
 * @returns Array of assets in the format expected by TransferList
 */
export const convertToAssets = (servers: Server[] = [], databases: Database[] = []): Asset[] => {
  // Convert servers to assets
  const serverAssets: Asset[] = servers.map((server) => ({
    assetId: server.server_id,
    assetName: server.server_name,
    assetType: "server",
    app_ids: server.app_ids ?? [],
    server_os_family: server.server_os_family,
    server_fqdn: server.server_fqdn,
    server_tier: server.server_tier,
    server_environment: server.server_environment,
    r_type: server.r_type,
    move_group_id: server.move_group_id ? server.move_group_id : undefined,
    wpm_job_id: server.wpm_job_id,
  }));

  // Convert databases to assets
  const databaseAssets: Asset[] = databases.map((db) => ({
    assetId: db.database_id,
    assetName: db.database_name,
    assetType: "database",
    app_ids: db.app_ids ?? [],
    database_type: db.database_type,
    r_type: db.r_type || "",
    move_group_id: db.move_group_id ? db.move_group_id : undefined,
    wpm_job_id: db.wpm_job_id,
  }));

  // Combine and return all assets
  return [...serverAssets, ...databaseAssets];
};

/**
 * Converts Asset objects back to fully typed Server and Database objects
 * by merging with existing server and database data
 *
 * @param assets - Array of Asset objects to convert
 * @param wpmServers - Array of existing Server objects to merge with
 * @param wpmDatabases - Array of existing Database objects to merge with
 * @returns Object containing arrays of fully typed Server and Database objects
 */
export const convertFromAssets = (
  assets: Asset[],
  wpmServers: Server[],
  wpmDatabases: Database[]
): { servers: Server[]; databases: Database[] } => {
  const servers: Server[] = [];
  const databases: Database[] = [];

  assets.forEach((asset) => {
    if (asset.assetType === "server") {
      // Find matching existing server
      const existingServer = wpmServers.find((s) => s.server_id === asset.assetId);

      if (existingServer) {
        // Merge existing server with asset data (asset data move group of takes precedence)
        servers.push({
          ...existingServer,
          // Set move_group_id to null if it's undefined, otherwise use the value
          move_group_id: asset.move_group_id || "",
        });
      }
    } else if (asset.assetType === "database") {
      // Find matching existing database
      const existingDatabase = wpmDatabases.find((d) => d.database_id === asset.assetId);

      if (existingDatabase) {
        // Merge existing database with asset data (asset data move group id takes precedence)
        databases.push({
          ...existingDatabase,
          move_group_id: asset.move_group_id || "",
        });
      }
    }
  });

  return { servers, databases };
};

/**
 * Helper function to update move group IDs for assets
 * @param assets - Array of assets to update
 * @param moveGroupId - Move group ID to assign
 * @returns Updated array of assets with new move group ID
 */
export const updateAssetMoveGroups = (assets: Asset[], moveGroupId: string): Asset[] => {
  return assets.map((asset) => ({
    ...asset,
    move_group_id: moveGroupId,
  }));
};
