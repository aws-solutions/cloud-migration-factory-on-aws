/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { entityAccessFromPermissions } from "./entity-access-from-permissions";

const permissionsData = {
  policies: [
    {
      policy_id: "1",
      entity_access: [
        {
          create: false,
          update: false,
          schema_name: "application",
          read: true,
          delete: false,
        },
        {
          create: false,
          update: false,
          schema_name: "wave",
          read: true,
          delete: false,
        },
        {
          create: false,
          update: false,
          schema_name: "server",
          read: true,
          delete: false,
        },
      ],
      policy_name: "ReadOnly",
    },
    {
      policy_id: "2",
      entity_access: [
        {
          create: true,
          update: true,
          attributes: [
            {
              attr_type: "application",
              attr_name: "app_id",
            },
            {
              attr_type: "application",
              attr_name: "app_name",
            },
            {
              attr_type: "application",
              attr_name: "wave_id",
            },
            {
              attr_type: "application",
              attr_name: "aws_accountid",
            },
            {
              attr_type: "application",
              attr_name: "aws_region",
            },
          ],
          schema_name: "application",
          read: true,
          delete: true,
        },
        {
          create: true,
          update: true,
          attributes: [
            {
              attr_type: "wave",
              attr_name: "wave_id",
            },
            {
              attr_type: "wave",
              attr_name: "wave_name",
            },
            {
              attr_type: "wave",
              attr_name: "wave_status",
            },
            {
              attr_type: "wave",
              attr_name: "wave_start_time",
            },
            {
              attr_type: "wave",
              attr_name: "wave_end_time",
            },
          ],
          schema_name: "wave",
          read: true,
          delete: true,
        },
        {
          create: true,
          update: true,
          attributes: [
            {
              attr_type: "server",
              attr_name: "server_id",
            },
            {
              attr_type: "server",
              attr_name: "app_id",
            },
            {
              attr_type: "server",
              attr_name: "server_name",
            },
            {
              attr_type: "server",
              attr_name: "server_os_family",
            },
            {
              attr_type: "server",
              attr_name: "server_os_version",
            },
            {
              attr_type: "server",
              attr_name: "server_fqdn",
            },
            {
              attr_type: "server",
              attr_name: "server_tier",
            },
            {
              attr_type: "server",
              attr_name: "server_environment",
            },
            {
              attr_type: "server",
              attr_name: "subnet_IDs",
            },
            {
              attr_type: "server",
              attr_name: "securitygroup_IDs",
            },
            {
              attr_type: "server",
              attr_name: "subnet_IDs_test",
            },
            {
              attr_type: "server",
              attr_name: "securitygroup_IDs_test",
            },
            {
              attr_type: "server",
              attr_name: "instanceType",
            },
            {
              attr_type: "server",
              attr_name: "iamRole",
            },
            {
              attr_type: "server",
              attr_name: "private_ip",
            },
            {
              attr_type: "server",
              attr_name: "tags",
            },
            {
              attr_type: "server",
              attr_name: "tenancy",
            },
            {
              attr_type: "server",
              attr_name: "migration_status",
            },
            {
              attr_type: "server",
              attr_name: "replication_status",
            },
            {
              attr_type: "server",
              attr_name: "r_type",
            },
            {
              attr_type: "server",
              attr_name: "network_interface_id",
            },
            {
              attr_type: "server",
              attr_name: "network_interface_id_test",
            },
            {
              attr_type: "server",
              attr_name: "dedicated_host_id",
            },
          ],
          schema_name: "server",
          read: true,
          delete: true,
        },
        {
          create: true,
          update: true,
          attributes: [
            {
              attr_type: "database",
              attr_name: "database_id",
            },
            {
              attr_type: "database",
              attr_name: "app_id",
            },
            {
              attr_type: "database",
              attr_name: "database_name",
            },
            {
              attr_type: "database",
              attr_name: "database_type",
            },
          ],
          schema_name: "database",
          read: true,
          delete: true,
        },
        {
          create: true,
          schema_name: "mgn",
        },
        {
          create: true,
          schema_name: "ce",
        },
        {
          create: true,
          schema_name: "ssm_job",
        },
        {
          create: true,
          update: true,
          attributes: [
            {
              attr_type: "script",
              attr_name: "script_name",
            },
            {
              attr_type: "script",
              attr_name: "script_description",
            },
            {
              attr_type: "script",
              attr_name: "fileName",
            },
            {
              attr_type: "script",
              attr_name: "path",
            },
            {
              attr_type: "script",
              attr_name: "script_masterfile",
            },
            {
              attr_type: "script",
              attr_name: "default",
            },
            {
              attr_type: "script",
              attr_name: "latest",
            },
          ],
          schema_name: "script",
        },
      ],
      policy_name: "Administrator",
    },
  ],
  roles: [
    {
      groups: [
        {
          group_name: "readonly",
        },
        {
          group_name: "admin",
        },
      ],
      role_id: "1",
      policies: [
        {
          policy_id: "1",
        },
        {
          policy_id: "2",
        },
      ],
      role_name: "FactoryAdmin",
    },
  ],
  groups: [
    {
      group_name: "readonly",
    },
    {
      group_name: "admin",
    },
  ],
  users: [
    {
      userRef: "0cabc3a2-c2b3-4612-9365-c20af7716a58",
      enabled: true,
      status: "CONFIRMED",
      groups: [
        {
          group_name: "admin",
        },
        {
          group_name: "readonly",
        },
      ],
      email: "serviceaccount@example.com",
      mfaEnabled: false,
    },
  ],
};

test("it builds the entity access record", () => {
  // GIVEN
  const groups = ["admin"];

  // WHEN
  const result = entityAccessFromPermissions(permissionsData, groups);

  // THEN
  expect(result).toEqual({
    application: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "application",
          attr_name: "app_id",
        },
        {
          attr_type: "application",
          attr_name: "app_name",
        },
        {
          attr_type: "application",
          attr_name: "wave_id",
        },
        {
          attr_type: "application",
          attr_name: "aws_accountid",
        },
        {
          attr_type: "application",
          attr_name: "aws_region",
        },
      ],
    },
    wave: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "wave",
          attr_name: "wave_id",
        },
        {
          attr_type: "wave",
          attr_name: "wave_name",
        },
        {
          attr_type: "wave",
          attr_name: "wave_status",
        },
        {
          attr_type: "wave",
          attr_name: "wave_start_time",
        },
        {
          attr_type: "wave",
          attr_name: "wave_end_time",
        },
      ],
    },
    server: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "server",
          attr_name: "server_id",
        },
        {
          attr_type: "server",
          attr_name: "app_id",
        },
        {
          attr_type: "server",
          attr_name: "server_name",
        },
        {
          attr_type: "server",
          attr_name: "server_os_family",
        },
        {
          attr_type: "server",
          attr_name: "server_os_version",
        },
        {
          attr_type: "server",
          attr_name: "server_fqdn",
        },
        {
          attr_type: "server",
          attr_name: "server_tier",
        },
        {
          attr_type: "server",
          attr_name: "server_environment",
        },
        {
          attr_type: "server",
          attr_name: "subnet_IDs",
        },
        {
          attr_type: "server",
          attr_name: "securitygroup_IDs",
        },
        {
          attr_type: "server",
          attr_name: "subnet_IDs_test",
        },
        {
          attr_type: "server",
          attr_name: "securitygroup_IDs_test",
        },
        {
          attr_type: "server",
          attr_name: "instanceType",
        },
        {
          attr_type: "server",
          attr_name: "iamRole",
        },
        {
          attr_type: "server",
          attr_name: "private_ip",
        },
        {
          attr_type: "server",
          attr_name: "tags",
        },
        {
          attr_type: "server",
          attr_name: "tenancy",
        },
        {
          attr_type: "server",
          attr_name: "migration_status",
        },
        {
          attr_type: "server",
          attr_name: "replication_status",
        },
        {
          attr_type: "server",
          attr_name: "r_type",
        },
        {
          attr_type: "server",
          attr_name: "network_interface_id",
        },
        {
          attr_type: "server",
          attr_name: "network_interface_id_test",
        },
        {
          attr_type: "server",
          attr_name: "dedicated_host_id",
        },
      ],
    },
    database: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "database",
          attr_name: "database_id",
        },
        {
          attr_type: "database",
          attr_name: "app_id",
        },
        {
          attr_type: "database",
          attr_name: "database_name",
        },
        {
          attr_type: "database",
          attr_name: "database_type",
        },
      ],
    },
    mgn: {
      create: true,
      attributes: [],
    },
    ce: {
      create: true,
      attributes: [],
    },
    ssm_job: {
      create: true,
      attributes: [],
    },
    script: {
      create: true,
      update: true,
      attributes: [
        {
          attr_type: "script",
          attr_name: "script_name",
        },
        {
          attr_type: "script",
          attr_name: "script_description",
        },
        {
          attr_type: "script",
          attr_name: "fileName",
        },
        {
          attr_type: "script",
          attr_name: "path",
        },
        {
          attr_type: "script",
          attr_name: "script_masterfile",
        },
        {
          attr_type: "script",
          attr_name: "default",
        },
        {
          attr_type: "script",
          attr_name: "latest",
        },
      ],
    },
  });
});

test("it merges the permissions of 2 groups", () => {
  // GIVEN
  const groups = ["readonly", "admin"];

  // WHEN
  const result = entityAccessFromPermissions(permissionsData, groups);

  // THEN
  expect(result).toEqual({
    application: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "application",
          attr_name: "app_id",
        },
        {
          attr_type: "application",
          attr_name: "app_name",
        },
        {
          attr_type: "application",
          attr_name: "wave_id",
        },
        {
          attr_type: "application",
          attr_name: "aws_accountid",
        },
        {
          attr_type: "application",
          attr_name: "aws_region",
        },
      ],
    },
    wave: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "wave",
          attr_name: "wave_id",
        },
        {
          attr_type: "wave",
          attr_name: "wave_name",
        },
        {
          attr_type: "wave",
          attr_name: "wave_status",
        },
        {
          attr_type: "wave",
          attr_name: "wave_start_time",
        },
        {
          attr_type: "wave",
          attr_name: "wave_end_time",
        },
      ],
    },
    server: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "server",
          attr_name: "server_id",
        },
        {
          attr_type: "server",
          attr_name: "app_id",
        },
        {
          attr_type: "server",
          attr_name: "server_name",
        },
        {
          attr_type: "server",
          attr_name: "server_os_family",
        },
        {
          attr_type: "server",
          attr_name: "server_os_version",
        },
        {
          attr_type: "server",
          attr_name: "server_fqdn",
        },
        {
          attr_type: "server",
          attr_name: "server_tier",
        },
        {
          attr_type: "server",
          attr_name: "server_environment",
        },
        {
          attr_type: "server",
          attr_name: "subnet_IDs",
        },
        {
          attr_type: "server",
          attr_name: "securitygroup_IDs",
        },
        {
          attr_type: "server",
          attr_name: "subnet_IDs_test",
        },
        {
          attr_type: "server",
          attr_name: "securitygroup_IDs_test",
        },
        {
          attr_type: "server",
          attr_name: "instanceType",
        },
        {
          attr_type: "server",
          attr_name: "iamRole",
        },
        {
          attr_type: "server",
          attr_name: "private_ip",
        },
        {
          attr_type: "server",
          attr_name: "tags",
        },
        {
          attr_type: "server",
          attr_name: "tenancy",
        },
        {
          attr_type: "server",
          attr_name: "migration_status",
        },
        {
          attr_type: "server",
          attr_name: "replication_status",
        },
        {
          attr_type: "server",
          attr_name: "r_type",
        },
        {
          attr_type: "server",
          attr_name: "network_interface_id",
        },
        {
          attr_type: "server",
          attr_name: "network_interface_id_test",
        },
        {
          attr_type: "server",
          attr_name: "dedicated_host_id",
        },
      ],
    },
    database: {
      create: true,
      read: true,
      update: true,
      delete: true,
      attributes: [
        {
          attr_type: "database",
          attr_name: "database_id",
        },
        {
          attr_type: "database",
          attr_name: "app_id",
        },
        {
          attr_type: "database",
          attr_name: "database_name",
        },
        {
          attr_type: "database",
          attr_name: "database_type",
        },
      ],
    },
    mgn: {
      create: true,
      attributes: [],
    },
    ce: {
      create: true,
      attributes: [],
    },
    ssm_job: {
      create: true,
      attributes: [],
    },
    script: {
      create: true,
      update: true,
      attributes: [
        {
          attr_type: "script",
          attr_name: "script_name",
        },
        {
          attr_type: "script",
          attr_name: "script_description",
        },
        {
          attr_type: "script",
          attr_name: "fileName",
        },
        {
          attr_type: "script",
          attr_name: "path",
        },
        {
          attr_type: "script",
          attr_name: "script_masterfile",
        },
        {
          attr_type: "script",
          attr_name: "default",
        },
        {
          attr_type: "script",
          attr_name: "latest",
        },
      ],
    },
  });
});
