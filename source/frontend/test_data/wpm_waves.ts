/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { Wave } from "../src/models";

export const sampleWaves = (): Wave[] => [
  {
    wave_id: "wave-1",
    wave_name: "Wave 1 - Critical Systems",
    wave_status: "Planned",
    wave_start_time: "2023-11-01T08:00:00Z",
    wave_end_time: "2023-11-05T17:00:00Z",
    wave_servers_baseline: "25",
    wave_servers_forecast: "30",
    wave_apps_baseline: "5",
    wave_apps_forecast: "7",
    move_group_ids: ["mg-fa", "mg-hrs"],
    app_ids: ["app-001", "app-002", "app-003", "app-004", "app-005"],
    server_ids: ["srv-101", "srv-102", "srv-103", "srv-104", "srv-105", "srv-106", "srv-107"],
    server_count: 7,
    database_ids: ["db-201", "db-202", "db-203"],
    _history: {
      createdBy: { userRef: "user-001", email: "admin@example.com" },
      createdTimestamp: "2023-10-15T10:30:00Z",
    },
  },
  {
    wave_id: "wave-2",
    wave_name: "Wave 2 - Business Applications",
    wave_status: "Planned",
    wave_start_time: "2023-11-15T08:00:00Z",
    wave_end_time: "2023-11-20T17:00:00Z",
    wave_servers_baseline: "18",
    wave_servers_forecast: "22",
    wave_apps_baseline: "4",
    wave_apps_forecast: "6",
    move_group_ids: ["mg-cp"],
    app_ids: ["app-006", "app-007", "app-008", "app-009"],
    server_ids: ["srv-108", "srv-109", "srv-110", "srv-111", "srv-112"],
    server_count: 5,
    database_ids: ["db-204", "db-205", "db-206"],
    _history: {
      createdBy: { userRef: "user-001", email: "admin@example.com" },
      createdTimestamp: "2023-10-16T14:45:00Z",
    },
  },
  {
    wave_id: "wave-3",
    wave_name: "Wave 3 - Data Systems",
    wave_status: "Planned",
    wave_start_time: "2023-12-01T08:00:00Z",
    wave_end_time: "2023-12-05T17:00:00Z",
    wave_servers_baseline: "15",
    wave_servers_forecast: "18",
    wave_apps_baseline: "3",
    wave_apps_forecast: "4",
    move_group_ids: ["mg-dap"],
    app_ids: ["app-010", "app-011"],
    server_ids: ["srv-113", "srv-114", "srv-115", "srv-116", "srv-117", "srv-118"],
    server_count: 6,
    database_ids: ["db-207", "db-208", "db-209", "db-210"],
    _history: {
      createdBy: { userRef: "user-001", email: "admin@example.com" },
      createdTimestamp: "2023-10-17T09:15:00Z",
    },
  },
  {
    wave_id: "wave-4",
    wave_name: "Wave 4 - New wave manually created",
    wave_status: "Planned",
    wave_start_time: "2023-12-15T08:00:00Z",
    wave_end_time: "2023-12-20T17:00:00Z",
    wave_servers_baseline: "10",
    wave_servers_forecast: "12",
    wave_apps_baseline: "2",
    wave_apps_forecast: "3",
    move_group_ids: [],
    app_ids: [],
    server_ids: [],
    server_count: 0,
    database_ids: [],
    _history: {
      createdBy: { userRef: "user-001", email: "admin@example.com" },
      createdTimestamp: "2023-10-17T09:15:00Z",
    },
  },
];
