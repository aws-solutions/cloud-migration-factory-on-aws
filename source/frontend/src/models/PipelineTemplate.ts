export type PipelineTemplate = {
    pipeline_template_id: string;
    deletion_protection: boolean;
    pipeline_template_description: string;
    pipeline_template_name: string;
    version: string;
    _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
