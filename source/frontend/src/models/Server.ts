export type Server = {
  server_name: string;
  server_fqdn: string;
  server_os_version: string;
  server_os_family: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
  server_id: string;
  app_id: string;
  r_type: string;
};
