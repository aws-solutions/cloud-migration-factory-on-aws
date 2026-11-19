/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Meta, StoryObj } from "@storybook/react";
import { fn } from "@storybook/test";
import { Header, TableProps } from "@cloudscape-design/components";

import TransferList from "./TransferList";
import { MoveGroup } from "../../models/MoveGroup";
import { Wave } from "../../models/Wave";

import { wpmSchemas, sampleWaves, sampleMoveGroups } from "../../../test_data";
import { ErrorWithType } from "../../actions/ErrorHandlerHook";

// Define interfaces for our data types
interface Asset {
  assetId: string;
  assetName: string;
  assetType: "server" | "database";
  app_ids: string[];
  [key: string]: string | string[];
}

// Extend MoveGroup to include assets for the TransferList
interface MoveGroupWithAssets extends MoveGroup {
  assets: Asset[];
}

const meta: Meta<typeof TransferList<Wave, MoveGroup>> = {
  title: "TransferList",
  component: TransferList,
  parameters: {
    layout: "top",
    docs: {
      description: {
        component: `A UI component that accepts an array of records with one-to-many relationship attributes,
 renders two tables grouped by the relationship attribute, and allows transferring items between the tables.
 Memoized for better performance.`,
      },
    },
    design: {
      type: "figma",
      url: "https://www.figma.com/design/Bq7LwEwhEzMUxuPwPHv8Ng/Wave-Planning-Manager?node-id=1548-34255&t=DCVejkjywc14ibRl-0",
    },
  },
  tags: ["autodocs"],
  args: { onCancel: fn(), onConfirm: fn() },
};

export default meta;

type Story = StoryObj<typeof meta>;

const schemas = wpmSchemas();
const waves = sampleWaves();
const moveGroups = sampleMoveGroups();

const wavesAndMoveGroupsArgs = {
  header: (
    <Header
      variant="h3"
      description="Add or remove groups to migrate from a list of unassigned or assigned groups in pending jobs."
    >
      Manage Waves
    </Header>
  ),
  parent: {
    records: waves,
    labelAttribute: "wave_name",
    valueAttribute: "wave_id",
    selectedValue: waves[0].wave_id,
    multivalueRelationshipAttribute: "move_group_ids",
  },
  child: {
    records: moveGroups,
    valueAttribute: "move_group_id",
    schema: schemas.move_group,
    schemaName: "move_group",
  },
  onCancel: fn(),
  onConfirm: fn(),
  onUpdate: fn(),
} as const;

export const WavesAndMoveGroups: Story = {
  args: wavesAndMoveGroupsArgs,
};

// Mock data for servers
const mockServers: Asset[] = [
  {
    assetId: "srv-12345678",
    assetName: "webserver01",
    assetType: "server",
    server_os_family: "linux",
    server_fqdn: "webserver01.example.com",
    server_tier: "web",
    server_environment: "production",
    r_type: "Rehost",
    app_ids: ["app-87654321", "app-11223344"],
  },
  {
    assetId: "srv-23456789",
    assetName: "appserver01",
    assetType: "server",
    server_os_family: "linux",
    server_fqdn: "appserver01.example.com",
    server_tier: "app",
    server_environment: "production",
    r_type: "Rehost",
    app_ids: ["app-76543210"],
  },
  {
    assetId: "srv-34567890",
    assetName: "dbserver01",
    assetType: "server",
    server_os_family: "linux",
    server_fqdn: "dbserver01.example.com",
    server_tier: "database",
    server_environment: "production",
    r_type: "Replatform",
    app_ids: ["app-65432109", "app-55667788"],
  },
  {
    assetId: "srv-45678901",
    assetName: "winserver01",
    assetType: "server",
    server_os_family: "windows",
    server_fqdn: "winserver01.example.com",
    server_tier: "app",
    server_environment: "staging",
    r_type: "Rehost",
    app_ids: ["app-54321098"],
  },
  {
    assetId: "srv-56789012",
    assetName: "winserver02",
    assetType: "server",
    server_os_family: "windows",
    server_fqdn: "winserver02.example.com",
    server_tier: "web",
    server_environment: "staging",
    r_type: "Retire",
    app_ids: ["app-43210987", "app-22334455"],
  },
];

// Mock data for databases
const mockDatabases: Asset[] = [
  {
    assetId: "db-12345678",
    assetName: "CustomerDB",
    assetType: "database",
    database_type: "postgresql",
    r_type: "Replatform",
    app_ids: ["app-87654321"],
  },
  {
    assetId: "db-23456789",
    assetName: "InventoryDB",
    assetType: "database",
    database_type: "oracle",
    r_type: "Rehost",
    app_ids: ["app-76543210", "app-22334455"],
  },
  {
    assetId: "db-34567890",
    assetName: "PaymentProcessingDB",
    assetType: "database",
    database_type: "mysql",
    r_type: "Replatform",
    app_ids: ["app-65432109"],
  },
  {
    assetId: "db-45678901",
    assetName: "UserAuthDB",
    assetType: "database",
    database_type: "mssql",
    r_type: "Rehost",
    app_ids: ["app-54321098", "app-09876543"],
  },
  {
    assetId: "db-56789012",
    assetName: "AnalyticsDB",
    assetType: "database",
    database_type: "postgresql",
    r_type: "Rearchitect",
    app_ids: ["app-43210987"],
  },
];

// Mock data for move groups with assets
const mockMoveGroupsWithAssets: MoveGroupWithAssets[] = [
  {
    move_group_id: "mg-001",
    move_group_name: "Database Migration Group",
    wpm_job_id: "wpm-job-001",
    server_count: 3,
    total_server_storage: 450,
    complexity_score: 4.2,
    app_ids: ["app-87654321", "app-65432109", "app-11223344"],
    server_ids: ["srv-12345678", "srv-34567890"],
    database_ids: ["db-12345678", "db-34567890"],
    assets: [
      mockServers.find((s) => s.assetId === "srv-12345678"),
      mockServers.find((s) => s.assetId === "srv-34567890"),
      mockDatabases.find((d) => d.assetId === "db-12345678"),
      mockDatabases.find((d) => d.assetId === "db-34567890"),
    ].filter((a) => !!a),
  },
  {
    move_group_id: "mg-002",
    move_group_name: "Analytics Migration Group",
    wpm_job_id: "wpm-job-002",
    server_count: 4,
    total_server_storage: 800,
    complexity_score: 3.5,
    app_ids: ["app-76543210", "app-43210987", "app-55667788"],
    server_ids: ["srv-23456789"],
    database_ids: ["db-23456789", "db-56789012"],
    assets: [
      mockServers.find((s) => s.assetId === "srv-23456789"),
      mockDatabases.find((d) => d.assetId === "db-23456789"),
      mockDatabases.find((d) => d.assetId === "db-56789012"),
    ].filter((a) => !!a),
  },
  {
    move_group_id: "mg-003",
    move_group_name: "Authentication & Security Group",
    wpm_job_id: "wpm-job-003",
    server_count: 3,
    total_server_storage: 500,
    complexity_score: 3.2,
    app_ids: ["app-54321098", "app-09876543"],
    server_ids: ["srv-45678901"],
    database_ids: ["db-45678901"],
    assets: [
      mockServers.find((s) => s.assetId === "srv-45678901"),
      mockDatabases.find((d) => d.assetId === "db-45678901"),
    ].filter((a) => !!a),
  },
  {
    move_group_id: "mg-004",
    move_group_name: "Reporting & Catalog Group",
    wpm_job_id: "wpm-job-005",
    server_count: 3,
    total_server_storage: 350,
    complexity_score: 2.5,
    app_ids: ["app-21098765", "app-98765432"],
    server_ids: ["srv-56789012"],
    database_ids: [],
    assets: [mockServers.find((s) => s.assetId === "srv-56789012")].filter((a) => !!a),
  },
];

// Create a list of unassigned assets (not in any move group)
const assignedAssetIds = mockMoveGroupsWithAssets.flatMap((mg) => [...mg.server_ids, ...mg.database_ids]);
const unassignedAssets = [
  ...mockServers.filter((s) => !assignedAssetIds.includes(s.assetId)),
  ...mockDatabases.filter((d) => !assignedAssetIds.includes(d.assetId)),
];

// Create a mock move group for unassigned assets
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const unassignedMoveGroup: MoveGroupWithAssets = {
  move_group_id: "unassigned",
  move_group_name: "Unassigned Assets",
  wpm_job_id: "",
  server_count: unassignedAssets.filter((a) => a.assetType === "server").length,
  total_server_storage: 0,
  complexity_score: 0,
  app_ids: [],
  server_ids: unassignedAssets.filter((a) => a.assetType === "server").map((s) => s.assetId),
  database_ids: unassignedAssets.filter((a) => a.assetType === "database").map((d) => d.assetId),
  assets: unassignedAssets,
};

// Column definitions for the assets transfer list
const assetColumnDefinitions: TableProps.ColumnDefinition<Asset>[] = [
  {
    id: "assetName",
    header: "Asset Name",
    cell: (item: Asset) => item.assetName,
    sortingField: "assetName",
  },
  {
    id: "assetType",
    header: "Type",
    cell: (item: Asset) => (item.assetType === "server" ? "Server" : "Database"),
    sortingField: "assetType",
  },
  {
    id: "details",
    header: "Details",
    cell: (item: Asset) => {
      if (item.assetType === "server") {
        return `${item.server_os_family} | ${item.server_tier}`;
      } else {
        return `${item.database_type}`;
      }
    },
  },
  {
    id: "r_type",
    header: "Migration Strategy",
    cell: (item: Asset) => item.r_type,
    sortingField: "r_type",
  },
  {
    id: "app_ids",
    header: "Applications",
    cell: (item: Asset) => item.app_ids.join(),
    sortingField: "app_ids",
  },
];

export const MoveGroupsAndAssets: Story = {
  args: {
    header: (
      <Header variant="h3" description="Transfer assets between move groups to organize your migration.">
        Manage Assets in Move Groups
      </Header>
    ),
    parent: {
      records: mockMoveGroupsWithAssets,
      labelAttribute: "move_group_name",
      valueAttribute: "move_group_id",
      selectedValue: mockMoveGroupsWithAssets[0].move_group_id,
    },
    child: {
      records: [...mockServers, ...mockDatabases],
      valueAttribute: "assetId",
      columnDefinitions: assetColumnDefinitions,
    },
    onCancel: fn(),
    onConfirm: fn(),
  },
};

export const MoveGroupsAndAssetsWithFiltering: Story = {
  args: {
    ...MoveGroupsAndAssets.args,
    filteringProperties: [
      {
        propertyLabel: "Asset Type",
        propertyKey: "assetType",
        options: [
          { label: "Server", value: "server" },
          { label: "Database", value: "database" },
        ],
      },
      {
        propertyLabel: "Migration Strategy",
        propertyKey: "r_type",
        options: [
          { label: "Rehost", value: "Rehost" },
          { label: "Replatform", value: "Replatform" },
          { label: "Retire", value: "Retire" },
          { label: "Rearchitect", value: "Rearchitect" },
        ],
      },
    ],
  },
};

export const MoveGroupsAndAssetsWithSearch: Story = {
  args: {
    ...MoveGroupsAndAssets.args,
    searchable: true,
    searchableAttributes: ["assetName", "assetId"],
  },
};

export const WarningWhenConfirm: Story = {
  args: {
    ...MoveGroupsAndAssets.args,
    onConfirm: () =>
      new Promise((_, rej) => setTimeout(() => rej(new ErrorWithType("Some validation error", "warning")), 500)),
  },
};

export const ReadOnly: Story = {
  args: {
    ...wavesAndMoveGroupsArgs,
    readOnly: true,
  },
};

export const Loading: Story = {
  args: {
    ...wavesAndMoveGroupsArgs,
    isLoading: true,
  },
};
