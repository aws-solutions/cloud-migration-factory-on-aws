import botocore
from cmf_logger import logger
import io
import json
from pathlib import Path
from requests.models import Response
import sys
import zipfile

MGH_TEST_DESCRIBE_HOME_REGION_CONTROLS_DEFAULT = []
mgh_test_describe_home_region_controls_mock_value = []

MGH_TEST_GET_HOME_REGION_DEFAULT = None
mgh_test_get_home_region_mock_value = None

EXPORT_DOWNLOAD_URL = "s3.amazon.com/ads-export"
ADS_TEST_DESCRIBE_EXPORT_TASKS_DEFAULT = [{"exportStatus": "SUCCEEDED", "configurationsDownloadUrl": EXPORT_DOWNLOAD_URL}]
ads_test_describe_export_tasks_mock_value = ADS_TEST_DESCRIBE_EXPORT_TASKS_DEFAULT

ads_describe_config_override = None

def init():
    # This is to get around the relative path import issue.
    # Absolute paths are being used in this file after setting the root directory
    file = Path(__file__).resolve()
    package_root_directory = file.parents[1]
    sys.path.append(str(package_root_directory) + '/../../backend/lambda_unit_test/')
    sys.path.append(str(package_root_directory) + '/../../backend/lambda_layers/lambda_layer_utils/python/')
    sys.path.append(str(file.parents[0]))
    integrations_directory = str(file.parents[2])
    sys.path.append(integrations_directory)
    sys.path.append(integrations_directory + '/mgh/lambdas/')
    from cmf_logger import logger
    logger.debug(f'sys.path: {list(sys.path)}')

init()

mock_os_environ = {
    'AWS_ACCESS_KEY_ID': 'testing',
    'AWS_SECRET_ACCESS_KEY': 'testing',
    'AWS_SECURITY_TOKEN': 'testing',
    'AWS_SESSION_TOKEN': 'testing',
    'AWS_DEFAULT_REGION': 'us-east-1',
    'region': 'us-east-1',
    'application': 'cmf',
    'environment': 'unittest',
    'cors': "test-cors",
    'AnonymousUsageData': 'Yes',
    'solutionUUID': 'test_solution_UUID',
    'SOLUTION_ID': 'SO101',
    'SOLUTION_VERSION': '00000',
    'AWS_ACCOUNT_ID': '111111111111',
    'LOGIN_API': 'login-execute-api',
    'USER_API': 'user-execute-api',
    'USER_POOL_ID': 'userPoolId',
    'USER_POOL_CLIENT_ID': 'userPoolClientId',
    'ADMIN_API': 'admin-execute-api'
}

def get_mock_mgh_event(task_name, task_arguments):
    body = {**task_arguments, "action": task_name}
    return {
        "resource": "/mgh",
        "path": "/mgh",
        "httpMethod": "POST",
        "headers": {
            "Accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br"
        },
        "body": json.dumps(body)
    }


def mock_import_ads_discovery_task_arguments():
    return {
        "aws_accountid": "111122223333",
        "aws_region": "us-west-2",
        "home_region": "us-west-2",
        "r_type": "Rehost",
        "task_execution_id": "1"
    }


def get_mock_ec2_rec_task_arguments():
    return {
        "home_region": "us-west-2",
        "aws_region": "us-west-2",
        "ec2_instance_family_exclusions": ["T2"],
        "sizing_preference": "Percentile of utilization",
        "percent_of_cpu_specification": "50",
        "percent_of_ram_specification": "40",
        "current_server_specification_match_preference": "Custom Match",
        "task_execution_id": "1"
    }


def get_mock_create_home_region_task_arguments():
    return {
        "home_region": "us-west-2",
        "task_execution_id": "1"
    }


def mock_api_call_success():
    return {
        'ResponseMetadata': {
            'HTTPStatusCode': 200
        }
    }


def mock_start_export_task_response():
    response = mock_api_call_success()
    response['exportId'] = 'test-export-id'
    return response


def mock_requests_get_schema_with_unsupported_required_attribute(*args, **kwargs):
    for k in kwargs:
        if kwargs[k].endswith("/prod/admin/schema/app"):
            text = '{"schema_type": "user", "attributes": ' \
                       '[{"name": "app_id", "description": "Application Id", "system": true, "hidden": true, "type": "string", "required": true}, ' \
                       '{"system": true, "name": "unsupported", "description": "Unsupported", "validation_regex_msg": "Application name must be specified.", "group_order": "-1000", "type": "string", "required": true}, ' \
                       '{"system": true, "listvalue": "111122223333", "name": "aws_accountid", "description": "AWS Account Id", "validation_regex_msg": "Invalid AWS account Id.", "type": "list", "required": true, "group": "Target"}, ' \
                       '{"system": true, "listvalue": "us-east-2", "name": "aws_region", "description": "AWS Region", "type": "list", "required": true, "group": "Target"}], "schema_name": "app"}'
        if kwargs[k].endswith("/prod/admin/schema/server"):
            text = '{"schema_type": "user", "attributes": ' \
                   '[{"name": "server_id", "description": "Server Id", "system": true, "hidden": true, "type": "string", "required": true},' \
                   '{"rel_display_attribute": "app_name", "system": true, "rel_key": "app_id", "name": "app_id", "description": "Application", "rel_entity": "application", "group_order": "-998", "type": "relationship", "required": true},' \
                   '{"system": true, "name": "server_name", "description": "Server Name", "validation_regex_msg": "Server names must contain only alphanumeric, hyphen or period characters.", "group_order": "-1000", "type": "string", "required": true},' \
                   ' {"system": true, "listvalue": "windows,linux", "name": "server_os_family", "description": "Server OS Family", "validation_regex_msg": "Select a valid operating system.", "type": "list", "required": true}, ' \
                   '{"name": "unsupported", "description": "Unsupported", "system": true, "type": "string", "required": true}]}'
        return MockResponseToRequest(
                {"key1": "value1"},
                200,
                text
            )


def mock_successful_get_requests(*args, **kwargs):
    if EXPORT_DOWNLOAD_URL in args:
        # Mocking 1 server with a recommendation, 1 server not in CMF inventory, and 1 server without a recommendation
        mf = io.BytesIO()
        content = "ServerId,Server.ExternalId,Server.HostName,Server.VMware.VMname,Recommendation.EC2.Remarks,Server.OS.Name,Server.OS.Version,Server.CPU.NumberOfProcessors,Server.CPU.NumberOfCores,Server.CPU.NumberOfLogicalCores,Recommendation.EC2.RequestedCPU.UsagePct,Recommendation.EC2.RequestedvCPU,Server.RAM.TotalSizeInMB,Recommendation.EC2.RequestedRAM.UsagePct,Recommendation.EC2.RequestedRAMinMB,Recommendation.EC2.Instance.Model,Recommendation.EC2.Instance.vCPUCount,Recommendation.EC2.Instance.RAM.TotalSizeinMB,Recommendation.EC2.Instance.Price.UpfrontCost,Recommendation.EC2.Instance.Price.HourlyRate,Recommendation.EC2.Instance.Price.AmortizedHourlyRate,Recommendation.EC2.Instance.Price.EffectiveDate.UTC,Recommendation.EC2.Instance.OSType,UserPreference.Recommendation.CPUSizing,UserPreference.Recommendation.RAMSizing,UserPreference.Region,UserPreference.EC2.Tenancy,UserPreference.EC2.PricingModel,UserPreference.EC2.PricingModel.ContractTerm,UserPreference.EC2.PricingModel.Payment,UserPreference.EC2.ExcludedInstances,Applications,Tags,Server.SMBiosId,Server.VMware.MoRefId,Server.VMware.VCenterId,Server.VMware.vCenterName,Server.VMware.vmFolderPath,Server.CPU.UsagePct.Avg,Server.CPU.UsagePct.Max,Server.RAM.UsedSizeInMB.Avg,Server.RAM.UsedSizeInMB.Max,Server.RAM.UsagePct.Avg,Server.RAM.UsagePct.Max,Server.NumberOfDisks,Server.DiskReadsPerSecondInKB.Avg,Server.DiskWritesPerSecondInKB.Avg,Server.DiskReadsPerSecondInKB.Max,Server.DiskWritesPerSecondInKB.Max,Server.DiskReadOpsPerSecond.Avg,Server.DiskWriteOpsPerSecond.Avg,Server.DiskReadOpsPerSecond.Max,Server.DiskWriteOpsPerSecond.Max,Server.NetworkReadsPerSecondInKB.Avg,Server.NetworkWritesPerSecondInKB.Avg,Server.NetworkReadsPerSecondInKB.Max,Server.NetworkWritesPerSecondInKB.Max" \
               "\nd-server-1,,test.hostname.com,,,Linux,2.0.0.11,4,8,16,100,16,12005.376,100,12005.376,c6a.4xlarge,16,32768,0,0.612,0.612,2024-01-30 22:07:49,Linux,Specification,Specification,US West (Oregon),SHARED,On-Demand,,,,LinuxApp,,,,,,,67.22,98.34,2000.896,6002.688,16.666666666666668,50,,175.5772253,52.76470577,1175.577225,152.7647058,2.772252841,772.4508703,12.77225284,1031.231092,21.51860774,26.62745087,121.5186077,225.6274509" \
               "\nd-server-not-found,,test.hostname.com,,,Linux,2.0.0.11,4,8,16,100,16,12005.376,100,12005.376,c6a.4xlarge,16,32768,0,0.612,0.612,2024-01-30 22:07:49,Linux,Specification,Specification,US West (Oregon),SHARED,On-Demand,,,,LinuxApp,,,,,,,67.22,98.34,2000.896,6002.688,16.666666666666668,50,,175.5772253,52.76470577,1175.577225,152.7647058,2.772252841,772.4508703,12.77225284,1031.231092,21.51860774,26.62745087,121.5186077,225.6274509" \
               "\nserver0,,test.hostname.com,,,Linux,2.0.0.11,4,8,16,100,16,12005.376,100,12005.376,,16,32768,0,0.612,0.612,2024-01-30 22:07:49,Linux,Specification,Specification,US West (Oregon),SHARED,On-Demand,,,,LinuxApp,,,,,,,67.22,98.34,2000.896,6002.688,16.666666666666668,50,,175.5772253,52.76470577,1175.577225,152.7647058,2.772252841,772.4508703,12.77225284,1031.231092,21.51860774,26.62745087,121.5186077,225.6274509"

        with zipfile.ZipFile(mf, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('EC2InstanceRecommendations.csv', str.encode(content))
        response = Response()
        response._content = mf.getvalue()
        return response
    for k in kwargs:
        if kwargs[k].endswith("/prod/admin/schema/app"):
            text = '{"schema_type": "user", "attributes": ' \
                   '[{"name": "app_id", "description": "Application Id", "system": true, "hidden": true, "type": "string", "required": true}, ' \
                   '{"system": true, "name": "app_name", "description": "Application Name", "validation_regex_msg": "Application name must be specified.", "group_order": "-1000", "type": "string", "required": true},' \
                   '{"system": true, "rel_display_attribute": "wave_name", "rel_key": "wave_id", "name": "wave_id", "description": "Wave Id", "rel_entity": "wave", "group_order": "-999", "type": "relationship", "required": false}, ' \
                   '{"system": true, "listvalue": "111122223333", "name": "aws_accountid", "description": "AWS Account Id", "validation_regex_msg": "Invalid AWS account Id.", "type": "list", "required": true, "group": "Target"},' \
                   '{"system": true, "listvalue": "us-east-2", "name": "aws_region", "description": "AWS Region", "type": "list", "required": true, "group": "Target"}], "schema_name": "app"}'
        if kwargs[k].endswith("/prod/user/app"):
            text = '[{"aws_region": "us-west-2", "app_id": "1", "aws_accountid": "111122223333", "app_name": "app1"}, ' \
                   '{"aws_region": "us-east-1", "app_id": "2", "aws_accountid": "222233334444", "app_name": "app2"}]'
        if kwargs[k].endswith("/prod/admin/schema/server"):
            text = '{"schema_type": "user", "attributes": ' \
                   '[{"name": "server_id", "description": "Server Id", "system": true, "hidden": true, "type": "string", "required": true},' \
                   '{"rel_display_attribute": "app_name", "system": true, "rel_key": "app_id", "name": "app_id", "description": "Application", "rel_entity": "application", "group_order": "-998", "type": "relationship", "required": true},' \
                   '{"system": true, "name": "server_name", "description": "Server Name", "validation_regex_msg": "Server names must contain only alphanumeric, hyphen or period characters.", "group_order": "-1000", "type": "string", "required": true},' \
                   '{"system": true, "listvalue": "windows,linux", "name": "server_os_family", "description": "Server OS Family", "validation_regex_msg": "Select a valid operating system.", "type": "list", "required": true},' \
                   '{"name": "server_os_version", "description": "Server OS Version", "system": true, "type": "string", "required": true},' \
                   '{"system": true, "name": "server_fqdn", "description": "Server FQDN", "validation_regex_msg": "Server FQDN must contain only alphanumeric, hyphen or period characters.", "group_order": "-999", "type": "string", "required": true},' \
                   '{"name": "server_environment", "description": "Server Environment", "group_order": "-997", "system": true, "type": "string"},' \
                   '{"name": "r_type", "system": true, "type": "string"}]}'
        if kwargs[k].endswith("/prod/user/server"):
            text = '[{"server_name": "server0", "server_os_family": "windows", "app_id": "1", "server_id": "54", "server_fqdn": "hostname.com", "r_type": "Rehost", "server_os_version": "6.2.0"},' \
                   '{"server_name": "d-server-1", "server_os_family": "linux", "app_id": "1", "server_id": "54", "server_fqdn": "hostname.com", "r_type": "Rehost", "server_os_version": "6.2.0"}]'
        return MockResponseToRequest(
            {"key1": "value1"},
            200,
            text
        )


def mock_missing_app_request(*args, **kwargs):
    for k in kwargs:
        if kwargs[k].endswith("/prod/user/app"):
            return MockResponseToRequest(
                {"key1": "value1"},
                200,
                '[]'
            )
        else:
            return mock_successful_get_requests(*args, **kwargs)


def mock_factory_login(silent, mf_config):
    return "token"


def mock_app_list_configs_response():
    response = mock_api_call_success()
    response['configurations'] = [{'application.name': 'app1'}, {'application.name': 'app2'}, {'application.name': 'app3'}]
    return response


def mock_server_list_configs_response():
    response = mock_api_call_success()
    response['configurations'] = [{'server.configurationId': 'd-server-1', 'server.source': 'Agent'},
                                  {'server.configurationId': 'd-server-2', 'server.source': 'Agent'},
                                  {'server.configurationId': 'd-server-3', 'server.source': 'Import'},
                                  {'server.configurationId': 'd-server-4', 'server.source': 'Import'}]
    return response


def mock_describe_configs_response(kwargs):
    response = mock_api_call_success()
    for k in kwargs:
        if 'd-server-1' in kwargs[k]:
            response['configurations'] = [{'server.applications': '[{"name": "app1"}]', 'server.configurationId': 'd-server-1', 'server.hostName': 'server1.hostname.com', 'server.osName': 'Linux - Amazon Linux release 2', 'server.osVersion': '2.0.0.0'}]
        if 'd-server-2' in kwargs[k]:
            response['configurations'] = [{'server.applications': '[{"name": "app2"}]', 'server.configurationId': 'd-server-2', 'server.hostName': 'server2.hostname.com', 'server.osName': 'Windows 2016', 'server.osVersion': '53.0.0.1'}]
        if 'd-server-3' in kwargs[k]:
            response['configurations'] = [{'server.configurationId': 'd-server-3', 'server.hostName': 'server1.hostname.com', 'server.osName': 'Linux - Amazon Linux release 2', 'server.osVersion': '2.0.0.0'}]
        if 'd-server-4' in kwargs[k]:
            response['configurations'] = [{'server.applications': '[{"name": "app2"}]', 'server.configurationId': 'd-server-2', 'server.hostName': 'server2.hostname.com', 'server.osName': 'Ubuntu', 'server.osVersion': '53.0.0.1'}]

    return response


def mock_request_success(*args, **kwargs):
    return MockResponseToRequest(
        "",
        200,
        "{}"
    )


def mock_request_failure(*args, **kwargs):
    return MockResponseToRequest(
        "",
        400,
        "{}"
    )


def mock_request_item_errors(*args, **kwargs):
    return MockResponseToRequest(
        "",
        200,
        '{"errors": "error"}'
    )


def mock_boto_api_call(obj, operation_name, kwarg):
    logger.debug(f'{obj}: operation_name = {operation_name}, kwarg = {kwarg}')
    orig_boto_api_call = botocore.client.BaseClient._make_api_call

    if operation_name == 'CreateHomeRegionControl' or operation_name == 'DeleteHomeRegionControl':
        return mock_api_call_success()
    elif operation_name == 'GetHomeRegion':
        response = mock_api_call_success()
        global mgh_test_get_home_region_mock_value
        response['HomeRegion'] = mgh_test_get_home_region_mock_value
        mgh_test_get_home_region_mock_value = MGH_TEST_GET_HOME_REGION_DEFAULT
        return response
    elif operation_name == 'DescribeHomeRegionControls':
        response = mock_api_call_success()
        global mgh_test_describe_home_region_controls_mock_value
        response['HomeRegionControls'] = mgh_test_describe_home_region_controls_mock_value
        mgh_test_describe_home_region_controls_mock_value = MGH_TEST_DESCRIBE_HOME_REGION_CONTROLS_DEFAULT
        return response
    elif operation_name == 'StartExportTask':
        return mock_start_export_task_response()
    elif operation_name == 'DescribeExportTasks':
        response = mock_api_call_success()
        global ads_test_describe_export_tasks_mock_value
        response['exportsInfo'] = ads_test_describe_export_tasks_mock_value
        ads_test_describe_export_tasks_mock_value = ADS_TEST_DESCRIBE_EXPORT_TASKS_DEFAULT
        return response
    elif operation_name == 'ListConfigurations':
        for k in kwarg:
            if kwarg[k].endswith('APPLICATION'):
                return mock_app_list_configs_response()
            if kwarg[k].endswith('SERVER'):
                return mock_server_list_configs_response()
    elif operation_name == 'DescribeConfigurations':
        global ads_describe_config_override
        if ads_describe_config_override is not None:
            response = ads_describe_config_override
            ads_describe_config_override = None
            return response
        return mock_describe_configs_response(kwarg)
    else:
        return orig_boto_api_call(obj, operation_name, kwarg)


# This class will be used by the mock function to replace requests.get
class MockResponseToRequest:
    def __init__(self, json_data, status_code, text):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text

    def json(self):
        return self.json_data