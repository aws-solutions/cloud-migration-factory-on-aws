import { CMFHistoryCreated } from "./Pipeline";

/**
 * Base rule with ID and audit attributes
 * @internal
 */
type BaseRuleWithIdAndAudit = {
  rule_id?: string;
  isDefault?: boolean;
  _history?: CMFHistoryCreated;
};

/**
 * Base rule data type containing common fields for all rule types
 * @internal
 */
type BaseRuleData = {
  rule_name: string;
  rule_description?: string;
  status: "ENABLED" | "DISABLED";
};

/**
 * Combined base rule type with both ID/audit attributes and common data fields
 * @internal
 */
type BaseWPMRule = BaseRuleWithIdAndAudit & BaseRuleData;

/**
 * WPM Job Rule - defines configuration parameters for Wave Planning Manager jobs
 * @property {string} rule_type - Always 'WPM_JOB' for this rule type
 * @property {object} [configuration] - Optional configuration parameters for the job
 * @property {string} [configuration.nomination_app_count] - Number of applications to nominate
 * @property {string} [configuration.wave_server_capacity] - Maximum server capacity per wave
 * @property {string} [configuration.wave_storage_capacity] - Maximum storage capacity per wave
 * @property {string} [configuration.starting_wave_server_capacity] - Initial server capacity for first wave
 * @property {string} [configuration.wave_server_capacity_increase] - Incremental increase in server capacity
 */
export type WPMJobRule = BaseWPMRule & {
  rule_type: "WPM_JOB";
  configuration?: {
    nomination_app_count?: string;
    wave_server_capacity?: string;
    wave_storage_capacity?: string;
    starting_wave_server_capacity?: string;
    wave_server_capacity_increase?: string;
  };
};

/**
 * Data structure for grouping rules
 * @property {"GROUPING_INCLUSIVE" | "GROUPING_EXCLUSIVE"} rule_type - Type of grouping rule
 * @property {Array<{asset_type: string, asset_key: string}>} relationships - Asset relationships to consider for grouping
 */
export type WPMGroupingRuleData = BaseRuleData & {
  rule_type: "GROUPING_INCLUSIVE" | "GROUPING_EXCLUSIVE";
  relationships: {
    asset_type: string;
    asset_key: string;
  }[];
};

/**
 * Grouping Rules (Inclusive/Exclusive) - defines how assets should be grouped together or kept separate
 * @property {"GROUPING_INCLUSIVE" | "GROUPING_EXCLUSIVE"} rule_type - Determines if assets should be kept together or apart
 * @property {Array<{asset_type: string, asset_key: string}>} relationships - Asset relationships to consider for grouping
 */
export type WPMGroupingRule = BaseRuleWithIdAndAudit & WPMGroupingRuleData;

/**
 * Defines criteria for scoring assets in prioritizing rules
 * @template T - Type for bound values (string or number)
 * @property {T} [upper_bound] - Upper bound for the scoring range
 * @property {T} [lower_bound] - Lower bound for the scoring range
 * @property {string} [value] - Exact value to match
 * @property {number|string} complexity_score - Score to assign when criteria is met
 * @internal
 */
type ScoringCriteria<T = string | number> = {
  upper_bound?: T;
  lower_bound?: T;
  value?: string;
  complexity_score: number | string;
};

/**
 * Data structure for prioritizing rules
 * @template T - Type for bound/level values (string or number)
 * @property {"PRIORITIZING"} rule_type - Always 'PRIORITIZING' for this rule type
 * @property {string} asset_type - Type of asset to prioritize
 * @property {string} attr_key - Asset attribute key to use for prioritization
 * @property {"SORTING" | "SCORING"} sub_type - Subtype determining prioritization method
 */
export type WPMPrioritizingRuleData<T = string | number> = BaseRuleData & {
  rule_type: "PRIORITIZING";
  asset_type: string;
  attr_key: string;
} & (
    | { sub_type: "SORTING"; sort_order: string; sort_level: T; sort_by_value?: string[] }
    | { sub_type: "SCORING"; scoring_criteria: ScoringCriteria<T>[] }
  );

/**
 * Prioritizing Rule - defines how assets should be prioritized during wave planning
 * @property {"PRIORITIZING"} rule_type - Always 'PRIORITIZING' for this rule type
 * @property {string} asset_type - Type of asset to prioritize
 * @property {string} attr_key - Asset attribute key to use for prioritization
 * @property {"SORTING" | "SCORING"} sub_type - Subtype determining prioritization method
 * @property {string} [sort_order] - For SORTING subtype: order direction
 * @property {number} [sort_level] - For SORTING subtype: priority level
 * @property {string[]} [sort_by_value] - For SORTING subtype: specific values to sort by
 * @property {ScoringCriteria<number>[]} [scoring_criteria] - For SCORING subtype: criteria for assigning scores
 */
export type WPMPrioritizingRule = BaseRuleWithIdAndAudit & WPMPrioritizingRuleData<number>;

/**
 * Database representation of Prioritizing Rule with string values for numeric fields
 * Used for the raw data retrieved via API where numbers are stored as strings
 */
export type WPMPrioritizingRuleInDB = BaseRuleWithIdAndAudit & WPMPrioritizingRuleData<string>;

/**
 * WPM rule data
 */
export type WPMRuleData = WPMGroupingRuleData | WPMPrioritizingRuleData;

/**
 * Union type for all WPM Rules - represents any type of rule used in Wave Planning Manager
 * Can be a WPMJobRule, GroupingRule, or PrioritizingRule
 */
export type WPMRule = WPMJobRule | WPMGroupingRule | WPMPrioritizingRule;

/**
 * Union type for all WPM Rules as stored in the database
 * Similar to WPMRule but uses PrioritizingRuleInDB for prioritizing rules
 */
export type WPMRuleInDB = WPMJobRule | WPMGroupingRule | WPMPrioritizingRuleInDB;

/**
 * The type for WPM Rule generation, also used by UI component to separate rules
 * @property {"PRIORITIZING"} - For prioritizing rules that determine app prioritization
 * @property {"GROUPING"} - For grouping rules that determine move groups
 */
export type WPMRuleGenerationType = "PRIORITIZING" | "GROUPING";
