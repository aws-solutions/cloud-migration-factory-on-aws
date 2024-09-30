import { rest } from "msw";
import { v4 } from "uuid";

export const mock_ssm_api = [
  rest.get("/ssm/scripts", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/ssm/jobs", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
  rest.get("/ssm", (request, response, context) => {
    return response(context.status(200), context.json([]));
  }),
];

export function generateTestAutomationJobs(count: number, data?: { appId: string }): Array<any> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  const currUUID = v4();
  const currDateString = new Date().toISOString();
  const instanceId = "i-0f8671916d904a820";
  return numbers.map((value) => {
    return {
      script: {
        default: "1",
        script_masterfile: "Verify-instance-status-wave-1.py",
        package_uuid: currUUID,
        _history: {
          createdBy: {
            userRef: "[system]",
            email: "[system]",
          },
          createdTimestamp: currDateString,
        },
        script_update_url: "",
        version_id: currUUID,
        script_arguments: {
          Waveid: 1,
        },
        script_dependencies: null,
        version: "0",
        script_description: "This script will do Verify instance status wave 1",
        script_name: "Verify instance status wave 1 - 2",
        latest: "1",
      },
      outputLastMessage: "All servers have had status check completed successfully",
      output:
        "[14:09:50] \nSuccessfully packaged [3-Verify Instance Status]\n\n\n[14:10:19]\n\n\nAll servers have had status check completed successfully.\n\n\n[14:10:38] \nJOB_COMPLETE\n\n",
      _history: {
        timeElapsed: "10",
        completedTimestamp: currDateString,
        outcomeDate: currDateString,
        createdBy: {
          userRef: currUUID,
          email: "example@example.com",
        },
        createdTimestamp: currDateString,
      },
      status: "COMPLETE",
      uuid: currUUID,
      SSMId: instanceId + "+" + currUUID + "+" + currDateString,
      mf_endpoints: {
        UserPoolClientId: "PoolClient_" + currUUID,
        Region: "us-east-1",
        LoginApiUrl: "https://login.example.com",
        UserApiUrl: "https://api.example.com",
        UserPoolId: "Pool_" + currUUID,
      },
      mi_id: instanceId,
      SSMAutomationExecutionId: currUUID,
      jobname: "Verify instance status wave 1 - 2",
    };
  });
}

export function generateTestAutomationScripts(count: number, data?: { appId: string }): Array<any> {
  const numbers = Array.from({ length: count }, (_, index) => index);
  return numbers.map((value, index) => ({
    version: "1",
    script_update_url: "",
    _history: {
      createdBy: {
        userRef: "[system]",
        email: "[system]",
      },
      createdTimestamp: "2023-04-25T17:46:51.337454",
    },
    script_description:
      "This script will verify the source servers meet the basic requirements for AWS MGN agent installation.",
    version_id: v4(),
    script_dependencies: null,
    script_arguments: [
      {
        name: "ReplicationServerIP",
        description: "Replication Server IP.",
        type: "standard",
        required: true,
        long_desc: "IP Address of an AWS MGN Replication EC2 Instance.",
      },
    ],
    lambda_function_name_suffix: 'ssm',
    type: 'Automated',
    script_masterfile: "0-Prerequisites-checks.py",
    default: "1",
    latest: index === 1 ? "2" : "1", // so that there is one entry with two versions
    package_uuid: v4(),
    script_name: "0-Check MGN Prerequisites " + index,
  }));
}
