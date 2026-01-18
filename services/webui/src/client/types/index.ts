// User types
export type UserRole = 'admin' | 'maintainer' | 'viewer';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CreateUserData {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface UpdateUserData {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

// Auth types
export interface LoginCredentials {
  email: string;
  password: string;
  tenant?: string;  // Tenant slug, defaults to "default"
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// API Response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// Navigation types
export interface NavItem {
  label: string;
  path: string;
  icon?: string;
  roles?: UserRole[];
}

export interface NavCategory {
  label: string;
  items: NavItem[];
  roles?: UserRole[];
}

// Tab types
export interface Tab {
  id: string;
  label: string;
  content?: React.ReactNode;
}

// PR Review types
export type ReviewStatus = 'pending' | 'approved' | 'changes_requested' | 'commented';
export type IssueSeverity = 'critical' | 'high' | 'medium' | 'low';
export type IssueStatus = 'open' | 'in_progress' | 'resolved' | 'closed';

export interface PullRequest {
  id: number;
  number: number;
  title: string;
  description: string;
  repository: string;
  author: string;
  status: ReviewStatus;
  created_at: string;
  updated_at: string;
  url: string;
}

export interface ReviewComment {
  id: number;
  author: string;
  content: string;
  created_at: string;
  line?: number;
  file?: string;
}

export interface Review {
  id: number;
  pull_request_id: number;
  pull_request: PullRequest;
  reviewer: string;
  status: ReviewStatus;
  comments: ReviewComment[];
  created_at: string;
  updated_at: string;
}

export interface Issue {
  id: number;
  title: string;
  description: string;
  repository: string;
  severity: IssueSeverity;
  status: IssueStatus;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  url: string;
}

export interface RepositoryConfig {
  id: number;
  name: string;
  url: string;
  access_token?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewMetrics {
  total_reviews: number;
  approved: number;
  changes_requested: number;
  pending: number;
  avg_review_time: number;
  total_issues: number;
  critical_issues: number;
  recent_activity: Array<{ date: string; count: number }>;
}

// Repository Management types
export type Platform = 'github' | 'gitlab' | 'git';
export type FindingSeverity = 'critical' | 'major' | 'minor' | 'suggestion';

export interface Repository {
  id: number;
  platform: Platform;
  repository: string;
  platform_organization?: string;
  display_name?: string;
  description?: string;
  enabled: boolean;
  polling_enabled: boolean;
  polling_interval_minutes: number;
  auto_review: boolean;
  review_on_open: boolean;
  review_on_sync: boolean;
  webhook_secret?: string;
  credential_id?: number;
  default_categories?: string[];
  default_ai_provider?: string;
  last_poll_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateRepositoryData {
  platform: Platform;
  repository: string;
  platform_organization?: string;
  display_name?: string;
  description?: string;
  enabled?: boolean;
  polling_enabled?: boolean;
  polling_interval_minutes?: number;
  auto_review?: boolean;
  credential_id?: number;
  default_categories?: string[];
  default_ai_provider?: string;
}

export interface UpdateRepositoryData {
  platform?: Platform;
  repository?: string;
  platform_organization?: string;
  display_name?: string;
  description?: string;
  enabled?: boolean;
  polling_enabled?: boolean;
  polling_interval_minutes?: number;
  auto_review?: boolean;
  credential_id?: number;
  default_categories?: string[];
  default_ai_provider?: string;
}

export interface RepositoryListResponse {
  repositories: Repository[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

export interface OrganizationsResponse {
  organizations: Record<string, string[]>;
}

// Dashboard Analytics types
export interface DashboardStats {
  overview: {
    total_repositories: number;
    total_reviews: number;
    pending_reviews: number;
  };
  findings: {
    critical: number;
    major: number;
    minor: number;
    suggestion: number;
  };
  platforms: Record<string, number>;
}

export interface Finding {
  id: number;
  review_id: number;
  file_path: string;
  line_start: number;
  line_end: number;
  severity: FindingSeverity;
  category: string;
  title: string;
  body: string;
  suggestion?: string;
  created_at: string;
  repository: {
    id: number;
    name: string;
    platform: Platform;
    display_name?: string;
  };
}

export interface FindingsResponse {
  findings: Finding[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

export interface DashboardFilters {
  platform?: Platform;
  organization?: string;
  repository_id?: number;
  severity?: FindingSeverity;
}

// Tenant types
export interface Tenant {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
  member_count?: number;
  team_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTenantData {
  name: string;
  slug: string;
  is_active?: boolean;
}

export interface UpdateTenantData {
  name?: string;
  slug?: string;
  is_active?: boolean;
}

export interface TenantMember {
  id: number;
  tenant_id: number;
  user_id: number;
  role: UserRole;
  user?: User;
  created_at: string;
}

export interface AddTenantMemberData {
  user_id: number;
  role: UserRole;
}

// Team types
export interface Team {
  id: number;
  tenant_id: number;
  name: string;
  slug: string;
  is_default: boolean;
  member_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTeamData {
  name: string;
  slug: string;
  is_default?: boolean;
}

export interface UpdateTeamData {
  name?: string;
  slug?: string;
  is_default?: boolean;
}

export interface TeamMember {
  id: number;
  team_id: number;
  user_id: number;
  role: UserRole;
  user?: User;
  created_at: string;
}

export interface AddTeamMemberData {
  user_id: number;
  role: UserRole;
}
