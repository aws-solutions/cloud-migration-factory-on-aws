/** Represents a mapping between source and target headers with confidence score */
export interface HeaderMapping {
  /** Original header name from the input data */
  readonly source_header: string;
  /** Mapped target header name in the schema */
  readonly target_header: string;
  /** Confidence score for the mapping (0.0 to 1.0) */
  readonly confidence: number;
}

/** Recommendation for unmapped headers */
export interface HeaderMappingRecommendation {
  /** Original header name that couldn't be mapped */
  readonly source_header: string;
  /** AI-recommended header name for manual review */
  readonly recommended_header: string;
  /** AI-recommended title name for manual review */
  readonly recommended_title: string;
}

/** Header mapping results for a specific entity type */
export interface HeaderMappingResponseEntity {
  /** Successfully mapped headers with confidence scores */
  readonly mappings: HeaderMapping[];
  /** Headers that couldn't be automatically mapped */
  readonly unmapped_attributes: string[];
  /** AI recommendations for unmapped headers */
  readonly recommendations: HeaderMappingRecommendation[];
}

/** Complete header mapping response for all entity types */
export interface HeaderMappingResponse {
  readonly [key: string]: HeaderMappingResponseEntity;
}
