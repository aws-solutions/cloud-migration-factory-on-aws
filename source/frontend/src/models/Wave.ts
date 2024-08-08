export type Wave = {
  wave_id: string;
  wave_name: string;
  wave_status?: string;
  _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
