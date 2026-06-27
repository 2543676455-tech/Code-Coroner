export type Mode = "professional" | "roast";
export type Status = "verified" | "partial" | "unsupported" | "unknown";

export interface Evidence {
  type: string;
  path: string;
  line_start?: number;
  line_end?: number;
  excerpt: string;
  description: string;
}

export interface Claim {
  id: string;
  claim: string;
  category: string;
  status: Status;
  confidence: number;
  reason: string;
  evidence: Evidence[];
}

export interface Check {
  id: string;
  name: string;
  status: "pass" | "fail" | "warn" | "unknown";
  message: string;
}

export interface Finding {
  rule_id: string;
  title: string;
  severity: string;
  path: string;
  line: number;
  excerpt: string;
  recommendation: string;
}

export interface Score {
  score: number;
  additions: string[];
  deductions: string[];
}

export interface Report {
  task_id: string;
  repository_url: string;
  mode: Mode;
  llm_enabled: boolean;
  repository_metadata: {
    name: string;
    owner: string;
    default_branch: string;
    commit_sha: string;
    file_count: number;
    python_files: number;
    lines_of_python: number;
  };
  project_structure: {
    top_level_entries: string[];
    package_directories: string[];
    entrypoints: string[];
    dependency_files: string[];
    configuration_files: string[];
    test_files: string[];
    largest_modules: Array<{ path: string; lines: number }>;
    max_module_lines: number;
    architecture_notes: string[];
  };
  claims: Claim[];
  engineering_checks: Check[];
  security_findings: Finding[];
  test_result: { status: string; duration_seconds: number; log: string; reason: string };
  scores: Record<"readme_credibility" | "production_readiness" | "learning_value" | "wrapper_index", Score>;
  summary: string;
  roast?: string;
}
