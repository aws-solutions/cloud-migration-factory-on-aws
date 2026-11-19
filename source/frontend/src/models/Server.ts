/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

export type Server = {
  // System fields
  server_id: string;
  server_name: string;
  server_fqdn: string;
  server_os_version: string;
  server_os_family: string;
  storage_size?: string;

  aws_region: string;
  aws_accountid: string;

  // Application related fields
  app_ids?: string[];

  // Server details
  server_tier?: string;
  server_environment?: string;

  // Migration related fields
  migration_status?: string;
  replication_status?: string;
  r_type: string;

  // WPM related fields
  move_group_id?: string;
  wpm_job_id?: string;
  wave_id?: string;

  // Target networking
  subnet_IDs?: string[];
  securitygroup_IDs?: string[];
  subnet_IDs_test?: string[];
  securitygroup_IDs_test?: string[];
  secondary_private_ip?: string[];
  private_ip?: string;
  network_interface_id?: string;
  network_interface_id_test?: string;

  // Target instance
  instanceType?: string;
  iamRole?: string;
  tags?: Record<string, string>;
  tenancy?: string;
  dedicated_host_id?: string;
  availabilityzone?: string;
  detailed_monitoring?: boolean;
  ami_id?: string;

  // Target storage
  root_vol_size?: number;
  root_vol_type?: string;
  root_vol_name?: string;
  add_vols_size?: string[];
  add_vols_type?: string[];
  add_vols_name?: string[];
  ebs_optimized?: boolean;
  ebs_kmskey_id?: string;

  // Migration automation
  secret_name?: string;
  server_mgn_post_launch?: string;
  server_source_shutdown_exclude?: boolean;
  mgn_replication_devices?: string;

  // Audit
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
