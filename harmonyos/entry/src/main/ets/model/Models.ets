export class HealthCounts {
  seals: number = 0;
  artifacts: number = 0;
}

export class HealthResponse {
  database: string = '';
  database_engine: string = '';
  ai: Object = {};
  counts: HealthCounts = new HealthCounts();
}

export class ArtifactRecord {
  id: string = '';
  kind: string = '';
  url: string = '';
  metadata: Object = {};
  created_at: string = '';
}

export class SealRecord {
  id: string = '';
  title: string = '';
  filename: string = '';
  sha256: string = '';
  created_at: string = '';
  source_kind: string = '';
  original_url: string = '';
  artifacts: ArtifactRecord[] = [];
}

export class DetailRouteParams {
  id: string;
  apiBaseUrl: string;

  constructor(id: string, apiBaseUrl: string) {
    this.id = id;
    this.apiBaseUrl = apiBaseUrl;
  }
}
