export interface Report {
  id: string; 
  title: string;
  acquirer_brand: string;
  target_brand: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'DRAFT';
  created_at: string;
  updated_at: string;
  user_id: number;
  analysis: ReportAnalysis | null;
  culture_clashes: CultureClash[];
  untapped_growths: UntappedGrowth[];
}

// Defines the structure for parsed JSON fields
export interface BrandArchetypeSummary { acquirer_archetype?: string, target_archetype?: string };
export interface CorporateEthosSummary { acquirer_ethos?: string, target_ethos?: string };
export interface PersonaExpansionSummary { expansion_score: number; latent_synergies: string[]; analysis: string };

export interface ReportAnalysis {
  id: number;
  cultural_compatibility_score: number;
  affinity_overlap_score: number;
  brand_archetype_summary: string | BrandArchetypeSummary; 
  strategic_summary: string;
  report_id: string; 
  persona_expansion_summary?: string | PersonaExpansionSummary;
  
  // This is the key addition. It's populated client-side to allow
  // components receiving `analysis` to access the full report.
  report: Report;

  // Source lists
  search_sources?: Array<{ title: string; url: string }>;
  acquirer_sources?: Array<{ title: string; url: string }>;
  target_sources?: Array<{ title: string; url: string }>;

  // Corporate culture fields
  acquirer_corporate_profile?: string;
  target_corporate_profile?: string;
  corporate_ethos_summary?: string | CorporateEthosSummary;
  acquirer_culture_sources?: Array<{ title: string; url: string }>;
  target_culture_sources?: Array<{ title:string; url: string }>;
  
  // Financial analysis fields
  acquirer_financial_profile?: string;
  target_financial_profile?: string;
  financial_synthesis?: string;
  acquirer_financial_sources?: Array<{ title: string; url: string }>;
  target_financial_sources?: Array<{ title: string; url: string }>;
}

export type ClashSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

export interface CultureClash {
  id: number;
  topic: string;
  description: string;
  severity: ClashSeverity;
  report_id: string;
}

export interface UntappedGrowth {
  id: number;
  description: string;
  potential_impact_score: number;
  report_id: string;
} 