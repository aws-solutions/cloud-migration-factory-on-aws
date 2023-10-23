#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


from unittest import mock

from moto import mock_dynamodb, mock_s3

from test_lambda_gfcommon import LambdaGFCommonTest, mock_getUserResourceCreationPolicy, default_mock_os_environ


@mock.patch.dict('os.environ', default_mock_os_environ)
@mock_dynamodb
@mock_s3
class LambdaGFValidationTest(LambdaGFCommonTest):

    @mock.patch.dict('os.environ', default_mock_os_environ)
    def setUp(self):
        import lambda_gfvalidation
        super().setUp(lambda_gfvalidation)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy')
    def test_lambda_handler_mfAuth_deny(self, mock_MFAuth):
        import lambda_gfvalidation
        self.assert_lambda_handler_mfAuth_deny(lambda_gfvalidation, mock_MFAuth)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_wave_id(self):
        import lambda_gfvalidation
        self.assert_lambda_handler_no_wave_id(lambda_gfvalidation)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_account_id(self):
        import lambda_gfvalidation
        self.assert_lambda_handler_no_account_id(lambda_gfvalidation)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_malformed_input(self):
        import lambda_gfvalidation
        self.assert_lambda_handler_malformed_input(lambda_gfvalidation)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_non_existent_wave_id(self):
        import lambda_gfvalidation
        self.assert_lambda_handler_non_existent_wave_id(lambda_gfvalidation)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_apps_table(self):
        import lambda_gfvalidation
        self.assert_lambda_hander_no_table_fail(lambda_gfvalidation,
                                                'apps_table',
                                                'ERROR: Unable to Retrieve Data from Dynamo DB App table')

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_servers_table(self):
        import lambda_gfvalidation
        self.assert_lambda_hander_no_table_fail(lambda_gfvalidation,
                                                'servers_table',
                                                'ERROR: Unable to Retrieve Data from Dynamo DB Server table')

    @mock.patch('lambda_gfdeploy.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_no_waves_table(self):
        import lambda_gfvalidation
        # returns success for this case !
        self.assert_lambda_hander_no_table(lambda_gfvalidation,
                                           'waves_table',
                                           'EC2 Input Validation Completed',
                                           200)

    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_success(self):
        import lambda_gfvalidation
        response = lambda_gfvalidation.lambda_handler(self.lambda_event_good, None)
        self.assertEqual(200, response['statusCode'])
        self.assertEqual('EC2 Input Validation Completed', response['body'])
        self.assert_servers_table_updated(lambda_gfvalidation.servers_table, 'Validation Completed')

    @mock.patch('lambda_gfvalidation.get_server_list')
    @mock.patch('lambda_gfvalidation.MFAuth.getUserResourceCreationPolicy', new=mock_getUserResourceCreationPolicy)
    def test_lambda_handler_exception_main(self, mock_get_server_list):
        import lambda_gfvalidation
        mock_get_server_list.side_effect = Exception('Exception in get_server_list')
        response = lambda_gfvalidation.lambda_handler(self.lambda_event_good, None)
        self.assertEqual(400, response['statusCode'])
        self.assertTrue(response['body'].startswith('Lambda Handler Main Function Failed with error : '))

    def test_validate_input(self):
        import lambda_gfvalidation
        apptotal = 2
        app_id = '1'
        app_name = 'app1'
        addvolcount = 0
        server = {'server_name': 'server1',
                  'instanceType': 't2.medium',
                  'securitygroup_IDs': ['sg-0485cd66e0f74adf3'],
                  'subnet_IDs': ['subnet-02ee1e6b9543b81c9'],
                  'tenancy': 'Shared',
                  'add_vols_size': [4, 8],
                  'add_vols_name': ['/dev/sdf', '/dev/sdg'],
                  'add_vols_type': ['standard', 'io1'],
                  'root_vol_size': '8',
                  'root_vol_name': '/dev/sda1',
                  'root_vol_type': 'io1',
                  'availabilityzone': 'us-east-1a',
                  'ami_id': 'amzn-linux-2022',
                  'ebs_optimized': True,
                  'detailed_monitoring': True
                  }

        # happy path
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual(None, response)

        # unequal length  add_vols_size and add_vols_name
        server['add_vols_size'] = [4]
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:Additional Volume Names are missing for some additional Volume, Please provide value '
                         'for all additional volumes or Leave as Blank to Use Default server1', response)
        server['add_vols_size'] = [4, 8]

        # invalid volume name
        server['add_vols_name'] = ['/dev/sdf_123', '/dev/sdg']
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:Additional Volume Name Is Incorrect for Server:server1 Allowed Values for Linux '
                         '"/dev/sdf","/dev/sdg","/dev/sdh","/dev/sdi","/dev/sdj","/dev/sdk","/dev/sdl","/dev/sdm",'
                         '"/dev/sdn","/dev/sdo","/dev/sdp", and for Window OS use "xvdf","xvdg","xvdh","xvdi","xvdj",'
                         '"xvdk","xvdl","xvdm","xvdn","xvdo","xvdp",""', response)
        server['add_vols_name'] = ['/dev/sdj', '/dev/sdi']

        # unequal length add_vols_size and add_vols_type
        server['add_vols_type'] = ['standard', 'io1', 'io2']
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:Additional Volume Types are missing for some additional Volume, Please provide value '
                         'for all additional volumes or Leave as Blank to Use Default server1', response)

        # invalid volume type
        server['add_vols_type'] = ['standard', 'io1_INVALID']
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:Additional Volume Type Is Incorrect for Server:server1 Allowed List of Volume Types '
                         '"standard", "io1", "io2", "gp2", "gp3" ', response)
        server['add_vols_type'] = ['gp3', 'io2']

        # invalid volume size : (int(volume_size) < 1 or (int(volume_size) > 16384)):
        server['add_vols_size'] = [0, 8]
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual(
            'ERROR:Additional Volume Size Is Incorrect for Server:server1 Volume Size needs to between 1 GiB and 16384 GiB',
            response)
        server['add_vols_size'] = [16385, 8]
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual(
            'ERROR:Additional Volume Size Is Incorrect for Server:server1 Volume Size needs to between 1 GiB and 16384 GiB',
            response)
        server['add_vols_size'] = [4, 8]

        # invalid root volume size
        server['root_vol_size'] = ''
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Root Volume Size field is empty for Server: server1', response)
        server['root_vol_size'] = '8'

        # no subnet ids
        server['subnet_IDs'] = []
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Subnet_IDs field is empty for Server: server1', response)
        server['subnet_IDs'] = ['subnet-02ee1e6b9543b81c9']

        # no security groups
        server['securitygroup_IDs'] = []
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The security group id is empty for Server: server1', response)
        server['securitygroup_IDs'] = ['sg-0485cd66e0f74adf3']

        # empty instance type
        server['instanceType'] = ''
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The instance type is empty for Server: server1', response)
        server['instanceType'] = 't2.medium'

        # invalid tenacy
        server['tenancy'] = 'Shared_INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The tenancy value is Invalid for Server: server1 Allowed Values '
                         '"Shared","Dedicated","Dedicated host" ', response)
        server['tenancy'] = 'Dedicated'

        # invalid root volume size : (int(root_vol_size)<8 or int(root_vol_size)>16384 )
        server['root_vol_size'] = '7'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Root Volume Size Is Incorrect for Server: server1 Volume Size needs '
                         'to between 8 GiB and 16384 GiB ', response)
        server['root_vol_size'] = '16385'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Root Volume Size Is Incorrect for Server: server1 Volume Size needs '
                         'to between 8 GiB and 16384 GiB ', response)
        server['root_vol_size'] = '8'

        # invalid root volume type
        server['root_vol_type'] = 'io1_INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Root Volume Type Is Incorrect for Server: server1 Allowed List of Volume Types '
                         '"standard", "io1", "io2", "gp2", "gp3"', response)
        server['root_vol_type'] = 'io1'

        # invalid root vol name
        server['root_vol_name'] = '/dev/sda1_INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The Root Volume Name Is Incorrect for Server: server1 Allowed List of Volume Names '
                         '"/dev/sda1", "/dev/xvda" ', response)
        server['root_vol_name'] = '/dev/xvda'

        # empty ami_id
        server['ami_id'] = ''
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The AMI Id Value is missing for Server: server1', response)
        server['ami_id'] = 'amzn-linux-2022'

        # empty availability zone
        server['availabilityzone'] = ''
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The availability zone is missing for Server: server1', response)
        server['availabilityzone'] = 'us-east-1a'

        # invalid ebs_optimized
        server['ebs_optimized'] = 'INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The ebs_optimized value is incorrect for Server : server1 '
                         'Allowed Values [true,false,""]', response)
        server['ebs_optimized'] = False

        # invalid detailed_monitoring
        server['detailed_monitoring'] = 'INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR:The detailed_monitoring value is incorrect for Server: server1 '
                         'Allowed Values [true,false,""]', response)
        server['detailed_monitoring'] = False

        # simulate unexpected error
        server['root_vol_size'] = 'INVALID'
        response = lambda_gfvalidation.validate_input(addvolcount, server)
        self.assertEqual('ERROR: EC2 Input Validation Failed.Failed With error: invalid literal for int() '
                         'with base 10: \'INVALID\'', response)
