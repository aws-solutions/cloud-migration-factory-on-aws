import {SessionState} from "../contexts/SessionContext";
import {v4} from "uuid";
import {AppChildProps} from "../models/AppChildProps";
import {NotificationContextType} from "../contexts/NotificationContext";
import {defaultSchemas} from "../../test_data/default_schema";

const defaultRoles = 'default_roles.json'
const defaultPolicies = 'default_policies.json'
const defaultGroups = 'default_groups.json'
const defaultUsers = 'default_users.json'

export const testRoles = require('../../test_data/' + defaultRoles);
export const testPolicies = require('../../test_data/' + defaultPolicies);
export const testGroups = require('../../test_data/' + defaultGroups);
export const testUsers = require('../../test_data/' + defaultUsers);

const TEST_USER_ACCESS = {
  "application": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true,
    "attributes": [
      {
        "attr_type": "application",
        "attr_name": "app_id"
      },
      {
        "attr_type": "application",
        "attr_name": "app_name"
      },
      {
        "attr_type": "application",
        "attr_name": "wave_id"
      },
      {
        "attr_type": "application",
        "attr_name": "aws_accountid"
      },
      {
        "attr_type": "application",
        "attr_name": "aws_region"
      }
    ]
  },
  "wave": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true,
    "attributes": [
      {
        "attr_type": "wave",
        "attr_name": "wave_id"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_name"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_status"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_start_time"
      },
      {
        "attr_type": "wave",
        "attr_name": "wave_end_time"
      }
    ]
  },
  "server": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true,
    "attributes": [
      {
        "attr_type": "server",
        "attr_name": "server_id"
      },
      {
        "attr_type": "server",
        "attr_name": "app_id"
      },
      {
        "attr_type": "server",
        "attr_name": "server_name"
      },
      {
        "attr_type": "server",
        "attr_name": "server_os_family"
      },
      {
        "attr_type": "server",
        "attr_name": "server_os_version"
      },
      {
        "attr_type": "server",
        "attr_name": "server_fqdn"
      },
      {
        "attr_type": "server",
        "attr_name": "server_tier"
      },
      {
        "attr_type": "server",
        "attr_name": "server_environment"
      },
      {
        "attr_type": "server",
        "attr_name": "subnet_IDs"
      },
      {
        "attr_type": "server",
        "attr_name": "securitygroup_IDs"
      },
      {
        "attr_type": "server",
        "attr_name": "subnet_IDs_test"
      },
      {
        "attr_type": "server",
        "attr_name": "securitygroup_IDs_test"
      },
      {
        "attr_type": "server",
        "attr_name": "instanceType"
      },
      {
        "attr_type": "server",
        "attr_name": "iamRole"
      },
      {
        "attr_type": "server",
        "attr_name": "private_ip"
      },
      {
        "attr_type": "server",
        "attr_name": "tags"
      },
      {
        "attr_type": "server",
        "attr_name": "tenancy"
      },
      {
        "attr_type": "server",
        "attr_name": "migration_status"
      },
      {
        "attr_type": "server",
        "attr_name": "replication_status"
      },
      {
        "attr_type": "server",
        "attr_name": "r_type"
      },
      {
        "attr_type": "server",
        "attr_name": "network_interface_id"
      },
      {
        "attr_type": "server",
        "attr_name": "network_interface_id_test"
      },
      {
        "attr_type": "server",
        "attr_name": "dedicated_host_id"
      }
    ]
  },
  "database": {
    "create": true,
    "read": true,
    "update": true,
    "delete": true,
    "attributes": [
      {
        "attr_type": "database",
        "attr_name": "database_id"
      },
      {
        "attr_type": "database",
        "attr_name": "app_id"
      },
      {
        "attr_type": "database",
        "attr_name": "database_name"
      },
      {
        "attr_type": "database",
        "attr_name": "database_type"
      }
    ]
  },
  "mgn": {
    "create": true,
    "attributes": []
  },
  "ce": {
    "create": true,
    "attributes": []
  },
  "ssm_job": {
    "create": true,
    "attributes": []
  },
  "script": {
    "create": true,
    "update": true,
    "attributes": [
      {
        "attr_type": "script",
        "attr_name": "script_name"
      },
      {
        "attr_type": "script",
        "attr_name": "script_description"
      },
      {
        "attr_type": "script",
        "attr_name": "fileName"
      },
      {
        "attr_type": "script",
        "attr_name": "path"
      },
      {
        "attr_type": "script",
        "attr_name": "script_masterfile"
      },
      {
        "attr_type": "script",
        "attr_name": "default"
      },
      {
        "attr_type": "script",
        "attr_name": "latest"
      }
    ]
  }
};

export const mockNotificationContext: NotificationContextType = {
  notifications: [],
  addNotification: jest.fn(),
  deleteNotification: jest.fn(),
  clearNotifications: jest.fn(),
  setNotifications: jest.fn(),
}

export const defaultTestProps: AppChildProps = {
  isReady: true,
  reloadPermissions(): Promise<unknown> {
    return Promise.resolve(undefined);
  },
  reloadSchema: () => Promise.resolve(() => {
  }),
  schemas: defaultSchemas,
  schemaIsLoading: false,
  schemaMetadata: [
    {
      "schema_name": "mgn",
      "schema_type": "automation",
      "friendly_name": "MGN"
    },
    {
      "schema_name": "policy",
      "schema_type": "system"
    },
    {
      "schema_name": "group",
      "schema_type": "system"
    },
    {
      "schema_name": "database",
      "schema_type": "user"
    },
    {
      "schema_name": "wave",
      "schema_type": "user"
    },
    {
      "schema_name": "EC2",
      "schema_type": "automation",
      "friendly_name": "EC2"
    },
    {
      "schema_name": "job",
      "schema_type": "automation",
      "friendly_name": "Job"
    },
    {
      "schema_name": "application",
      "schema_type": "user"
    },
    {
      "schema_name": "script",
      "schema_type": "system"
    },
    {
      "schema_name": "user",
      "schema_type": "system"
    },
    {
      "schema_name": "server",
      "schema_type": "user"
    },
    {
      "schema_name": "role",
      "schema_type": "system"
    },
    {
      "schema_name": "secret",
      "schema_type": "system"
    },
    {
      "schema_name": "ssm_job",
      "schema_type": "automation",
      "friendly_name": "Run Automation"
    }
  ],
  userEntityAccess: TEST_USER_ACCESS,
  userGroups: []

}

export const TEST_SESSION_STATE: SessionState = {
  idToken: v4(),
  accessToken: v4(),
  userName: 'test_user',
  userGroups: ['admin'],
}

export const TEST_SCHEMAS = [
  {
    "schema_name": "mgn",
    "schema_type": "automation",
    "friendly_name": "MGN"
  },
  {
    "schema_name": "policy",
    "schema_type": "system"
  },
  {
    "schema_name": "group",
    "schema_type": "system"
  },
  {
    "schema_name": "database",
    "schema_type": "user"
  },
  {
    "schema_name": "wave",
    "schema_type": "user"
  },
  {
    "schema_name": "EC2",
    "schema_type": "automation",
    "friendly_name": "EC2"
  },
  {
    "schema_name": "job",
    "schema_type": "automation",
    "friendly_name": "Job"
  },
  {
    "schema_name": "app",
    "schema_type": "user"
  },
  {
    "schema_name": "script",
    "schema_type": "system"
  },
  {
    "schema_name": "user",
    "schema_type": "system"
  },
  {
    "schema_name": "server",
    "schema_type": "user"
  },
  {
    "schema_name": "role",
    "schema_type": "system"
  },
  {
    "schema_name": "secret",
    "schema_type": "system"
  },
  {
    "schema_name": "ssm_job",
    "schema_type": "automation",
    "friendly_name": "Run Automation"
  }
];