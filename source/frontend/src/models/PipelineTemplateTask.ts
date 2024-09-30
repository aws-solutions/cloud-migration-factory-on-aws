export type PipelineTemplateTask = {
    pipeline_template_task_id: string;
    pipeline_template_id: string;
    pipeline_template_task_name: string;
    task_id: string;
    task_sequence_number: string;
    _history: { createdBy: { userRef: string; email: string }; createdTimestamp: string };
};
