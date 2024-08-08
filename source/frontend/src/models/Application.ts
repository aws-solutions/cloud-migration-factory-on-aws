export type Application = {
  app_id: string;
  app_name: string;
  aws_region: string;
  wave_id: string;
  aws_accountid: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
