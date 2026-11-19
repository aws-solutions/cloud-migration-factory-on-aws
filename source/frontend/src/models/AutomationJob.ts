export type Job = {
  readonly SSMId?: string;
  readonly mi_id?: string;
  readonly jobname: string;
  readonly outputLastMessage: string;
  readonly status: string;
  readonly SSMAutomationExecutionId: string;
  readonly uuid?: string;
  readonly script: {
    readonly script_name?: string;
    readonly package_uuid?: string;
    readonly default?: string;
    readonly script_description?: string;
    readonly script_masterfile?: string;
    readonly script_arguments?: Record<string, unknown>;
  };
};
