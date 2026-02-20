import { Meta, StoryObj } from "@storybook/react";
import ImportedEntitiesTable from "./ImportedEntitiesTable";
import { DeduplicatedEntity } from "../data-validation";
import { EntitySchema } from "../../models";
import "./ImportedEntitiesTable.css";

const meta: Meta<typeof ImportedEntitiesTable> = {
  component: ImportedEntitiesTable,
  title: "ImportedEntitiesTable",
};

export default meta;
type Story = StoryObj<typeof ImportedEntitiesTable>;

// Sample schema for application entity
const applicationSchema: EntitySchema = {
  schema_name: "application",
  schema_type: "entity",
  attributes: [
    {
      name: "app_name",
      type: "string",
      required: true,
      description: "",
    },
    {
      name: "description",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "environment",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "status",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "servers",
      type: "multivalue-string",
      required: false,
      description: "",
    },
  ],
};

// Sample schema for server entity
const serverSchema: EntitySchema = {
  schema_name: "server",
  schema_type: "entity",
  attributes: [
    {
      name: "server_name",
      type: "string",
      required: true,
      description: "",
    },
    {
      name: "ip_address",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "os_family",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "os_version",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "app_name",
      type: "string",
      required: false,
      rel_entity: "application",
      description: "",
    },
    {
      name: "storage_size",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "tenancy",
      type: "string",
      required: false,
      description: "",
    },
    {
      name: "environment",
      type: "string",
      required: false,
      description: "",
    },
  ],
};

// Sample application data
const applicationData: Record<string, Record<string, unknown>> = {
  app1: {
    app_name: "Application 1",
    description: "Sample application 1",
    environment: "Production",
    status: "Active",
    servers: "Server1,Server2",
  },
  app2: {
    app_name: "Application 2",
    description: "Sample application 2",
    environment: "Development",
    status: "Inactive",
    servers: "Server2,Server3,Server4",
  },
  app3: {
    app_name: "Application 3",
    description: "Sample application 3",
    environment: "Testing",
    status: "Active",
  },
};

// Sample server data
const serverData: Record<string, Record<string, unknown>> = {
  server1: {
    server_name: "Server 1",
    ip_address: "192.168.1.1",
    os_family: "Windows",
    os_version: "Server 2019",
    app_name: "app1",
    storage_size: "10",
    tenancy: "shared",
    environment: "dev",
  },
  server2: {
    server_name: "Server 2",
    ip_address: "192.168.1.2",
    os_family: "Linux",
    os_version: "Ubuntu 20.04",
    app_name: "app1",
    storage_size: "10",
    tenancy: "shared",
    environment: "dev",
  },
  server3: {
    server_name: "Server 3",
    ip_address: "192.168.1.3",
    os_family: "Windows",
    os_version: "Server 2016",
    app_name: "app2",
    storage_size: "10",
    tenancy: "shared",
    environment: "uat",
  },
  server4: {
    server_name: "Server 4",
    ip_address: "192.168.1.4",
    os_family: "Linux",
    os_version: "CentOS 8",
    app_name: "app3",
    storage_size: "20",
    tenancy: "shared",
    environment: "prod",
  },
};

// Sample deduplicated entities for create operations
const sampleEntitiesToCreate: DeduplicatedEntity[] = [
  {
    entityName: "application",
    schema: applicationSchema,
    data: applicationData,
  },
];

// Sample deduplicated entities for update operations
const sampleEntitiesToUpdate: DeduplicatedEntity[] = [
  {
    entityName: "server",
    schema: serverSchema,
    data: serverData,
  },
];

// Story for showing all entities
export const AllEntities: Story = {
  args: {
    entitiesToCreate: sampleEntitiesToCreate,
    entitiesToUpdate: sampleEntitiesToUpdate,
  },
};

// Story for showing filtered entities (only applications)
export const FilteredApplications: Story = {
  args: {
    entitiesToCreate: sampleEntitiesToCreate,
    entitiesToUpdate: sampleEntitiesToUpdate,
    entityFilter: "application",
  },
};

// Story for showing filtered entities (only servers)
export const FilteredServers: Story = {
  args: {
    entitiesToCreate: sampleEntitiesToCreate,
    entitiesToUpdate: sampleEntitiesToUpdate,
    entityFilter: "server",
  },
};

// Story for showing empty state
export const EmptyState: Story = {
  args: {
    entitiesToCreate: [],
    entitiesToUpdate: [],
  },
};
