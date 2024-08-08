import { rest } from "msw";
import { v4 } from "uuid";
import { Server } from "../../models/Server";
import { Database } from "../../models/Database";
import { Application } from "../../models/Application";
import { Wave } from "../../models/Wave";

export const mock_user_api = [
  rest.get("/user/server", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/user/database", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];

// generate an array with the given number of server records
export function generateTestServers(count: number, data?: { appId: string }): Array<Server> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    server_os_family: "linux",
    app_id: data?.appId ?? `1`,
    server_name: `unittest${number}`,
    server_id: `${number}`,
    server_fqdn: `unittest${number}.testdomain.local`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
    r_type: "Rehost",
    server_os_version: "redhat",
  }));
}

export function generateTestApps(count: number, data?: { waveId: string }): Array<Application> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    aws_region: "us-east-2",
    app_id: `${number}`,
    _history: {
      createdBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      lastModifiedTimestamp: "2023-09-19T19:02:30.593821",
      lastModifiedBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      createdTimestamp: "2023-09-15T21:58:59.182564",
    },
    app_name: `Unit testing App ${number}`,
    wave_id: data?.waveId ?? "1",
    aws_accountid: "123456789012",
  }));
}

export function generateTestWaves(count: number, data?: { waveStatus: string }): Array<Wave> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    wave_id: `${number}`,
    wave_name: `Unit testing Wave ${number}`,
    wave_status: data?.waveStatus ?? undefined,
    _history: {
      createdBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      lastModifiedTimestamp: "2023-09-19T19:02:30.593821",
      lastModifiedBy: {
        userRef: "47237551-331e-44a8-a00b-67c739ce9676",
        email: "foo@example.com",
      },
      createdTimestamp: "2023-09-15T21:58:59.182564",
    },
  }));
}

export function generateTestDatabases(count: number, data?: { appId: string }): Array<Database> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((number) => ({
    app_id: data?.appId ?? "1",
    database_type: "mysql",
    database_id: `${number}`,
    database_name: `unittest${number}`,
    _history: {
      createdBy: {
        userRef: v4(),
        email: "foo@example.com",
      },
      createdTimestamp: new Date().toISOString(),
    },
  }));
}
